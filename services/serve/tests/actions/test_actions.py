"""wp5: /v1/action stores validated leads, refuses bad payloads, and rate-limits."""

from __future__ import annotations

import uuid

import pytest

BOOKING = {"date": "2026-10-09", "time": "19:00", "party_size": 4,
           "name": "Test Guest", "contact": "guest@example.invalid"}
CATERING = {"date": "2026-11-05", "headcount": 40,
            "name": "Test Planner", "contact": "planner@example.invalid"}
CONTACT = {"form": "ui_form_contact",
           "values": {"name": "Test Guest", "email": "guest@example.invalid",
                      "phone": "617 555 0100", "topic": "General Inquiry",
                      "message": "Hello there"}}


@pytest.fixture()
def session_id(owner_conn):
    value = f"test-{uuid.uuid4()}"
    yield value
    owner_conn.execute("DELETE FROM ops.lead WHERE session_id = %s", (value,))
    owner_conn.commit()


def submit(client, name, payload, session_id, component):
    body = {"name": name, "payload": payload, "session_id": session_id, "component": component}
    return client.post("/v1/action", json=body)


def lead_row(owner_conn, lead_id):
    return owner_conn.execute(
        "SELECT kind, component, payload, channel, session_id FROM ops.lead WHERE id = %s",
        (lead_id,),
    ).fetchone()


def test_booking_request_stores_a_lead(client, owner_conn, session_id):
    response = submit(client, "submit_booking_request", BOOKING, session_id, "BookingForm")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    kind, component, payload, channel, stored_session = lead_row(owner_conn, body["lead_id"])
    assert (kind, component, channel, stored_session) == (
        "booking_request", "BookingForm", "web", session_id)
    assert payload == BOOKING
    assert "guest@example.invalid" not in response.text


def test_catering_quote_stores_a_lead(client, owner_conn, session_id):
    response = submit(client, "submit_catering_quote", CATERING, session_id, "CateringQuoteForm")
    assert response.status_code == 200
    kind, _, payload, _, _ = lead_row(owner_conn, response.json()["lead_id"])
    assert kind == "catering_quote"
    assert payload["headcount"] == 40


def test_configured_form_stores_a_form_lead(client, owner_conn, session_id):
    response = submit(client, "submit_form", CONTACT, session_id, "ui_form_contact")
    assert response.status_code == 200
    kind, component, payload, _, _ = lead_row(owner_conn, response.json()["lead_id"])
    assert (kind, component) == ("form", "ui_form_contact")
    assert payload["values"]["message"] == "Hello there"


def test_past_date_is_422(client, session_id):
    payload = {**BOOKING, "date": "2026-10-02"}
    response = submit(client, "submit_booking_request", payload, session_id, "BookingForm")
    assert response.status_code == 422
    body = response.json()
    assert body["ok"] is False
    assert {"field": "date", "message": "The date is in the past."} in body["errors"]


def test_party_size_out_of_range_is_422(client, session_id):
    payload = {**BOOKING, "party_size": 21}
    response = submit(client, "submit_booking_request", payload, session_id, "BookingForm")
    assert response.status_code == 422
    assert response.json()["errors"][0]["field"] == "party_size"


def test_unknown_form_and_bad_option_are_422(client, session_id):
    unknown = {"form": "ui_form_nope", "values": {}}
    assert submit(client, "submit_form", unknown, session_id, "x").status_code == 422
    bad = {**CONTACT, "values": {**CONTACT["values"], "topic": "Free money"}}
    response = submit(client, "submit_form", bad, session_id, "ui_form_contact")
    assert response.status_code == 422
    assert response.json()["errors"][0]["field"] == "topic"


def test_missing_required_form_field_is_422(client, session_id):
    values = {k: v for k, v in CONTACT["values"].items() if k != "message"}
    response = submit(client, "submit_form", {**CONTACT, "values": values}, session_id, "x")
    assert response.status_code == 422
    assert response.json()["errors"][0]["field"] == "message"


def test_card_number_is_never_stored(client, session_id):
    payload = {**BOOKING, "notes": "my card is 4242 4242 4242 4242"}
    response = submit(client, "submit_booking_request", payload, session_id, "BookingForm")
    assert response.status_code == 422
    assert response.json()["errors"][0]["field"] == "notes"


def test_fourth_lead_in_an_hour_is_refused(client, session_id):
    for _ in range(3):
        ok = submit(client, "submit_booking_request", BOOKING, session_id, "BookingForm")
        assert ok.status_code == 200
    refused = submit(client, "submit_booking_request", BOOKING, session_id, "BookingForm")
    assert refused.status_code == 429
    assert refused.json()["ok"] is False


def test_unknown_action_is_422(client, session_id):
    assert submit(client, "drop_tables", {}, session_id, "x").status_code == 422


def test_leads_are_counted_in_metrics(client, session_id):
    before = client.get("/v1/metrics").json()["leads_captured"]
    submit(client, "submit_catering_quote", CATERING, session_id, "CateringQuoteForm")
    assert client.get("/v1/metrics").json()["leads_captured"] == before + 1
