import { Field, FormStatus, str, useSubmit } from "./form";
import type { ComponentProps } from "./types";

interface BookingData {
  prefill?: { date?: unknown; time?: unknown; party_size?: unknown };
  booking_url?: string | null;
}

const KNOWN = ["date", "time", "party_size", "name", "contact", "notes"];

export function BookingForm({ data, ctx }: ComponentProps<BookingData>) {
  const pre = data?.prefill ?? {};
  const s = useSubmit(ctx, KNOWN, (v) => {
    const payload: Record<string, unknown> = {
      date: v.date,
      time: v.time,
      party_size: Number(v.party_size),
      name: v.name,
      contact: v.contact,
    };
    if (v.notes) payload.notes = v.notes;
    return ctx.submit("submit_booking_request", payload, "BookingForm");
  });
  if (data?.booking_url) {
    return (
      <div className="cac-form">
        <a className="cac-link" href={data.booking_url} target="_blank" rel="noopener noreferrer">
          Book on our booking page
        </a>
      </div>
    );
  }
  const e = s.errors;
  return (
    <form className="cac-form" onSubmit={s.onSubmit} aria-label="Booking request">
      <h3>Request a table</h3>
      <Field name="date" label="Date" type="date" required
        defaultValue={str(pre.date)} error={e.date} />
      <Field name="time" label="Time" type="time" required
        defaultValue={str(pre.time)} error={e.time} />
      <Field
        name="party_size"
        label="Party size"
        type="number"
        min={1}
        max={20}
        required
        defaultValue={str(pre.party_size)}
        error={e.party_size}
      />
      <Field name="name" label="Name" required error={e.name} />
      <Field name="contact" label="Phone or email" required error={e.contact} />
      <Field name="notes" label="Notes (optional)" textarea error={e.notes} />
      <p className="cac-form-note">This is a request; the restaurant will confirm.</p>
      <FormStatus notice={s.notice} topErrors={s.topErrors} sent={s.sent} />
      <button className="cac-btn" type="submit" disabled={s.busy}>
        {s.busy ? "Sending…" : "Send request"}
      </button>
    </form>
  );
}
