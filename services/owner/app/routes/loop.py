"""Flow 3 plumbing: topics, gaps, the owner's words, publish (SCHEMA 8.6)."""

import re
from datetime import date
from typing import Literal

import psycopg
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator, model_validator

from app.auth import require_any
from app.infra.db import get_conn
from app.routes.common import run
from app.services import owner_words, publisher, topics

router = APIRouter(prefix="/owner", tags=["gap loop"], dependencies=[Depends(require_any)])
TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class AnswerBody(BaseModel):
    gap_id: str = Field(min_length=1, max_length=80)
    answer_text: str

    @field_validator("answer_text")
    @classmethod
    def _owner_words(cls, value: str) -> str:
        text = value.strip()
        if not text or len(text) > 2000:
            raise ValueError("answer_text must be 1 to 2000 characters")
        if owner_words.has_card_or_ssn(text):
            raise ValueError("card and social security numbers are never stored")
        return text


class SpecialHoursBody(BaseModel):
    date: str
    closed: bool = False
    opens: str | None = None
    closes: str | None = None
    note: str | None = Field(None, max_length=200)

    @field_validator("date")
    @classmethod
    def _real_date(cls, value: str) -> str:
        if not DATE_RE.match(value):
            raise ValueError("date must be YYYY-MM-DD")
        date.fromisoformat(value)
        return value

    @model_validator(mode="after")
    def _times(self) -> "SpecialHoursBody":
        if self.closed:
            self.opens = self.closes = None
            return self
        if not (self.opens and self.closes and TIME_RE.match(self.opens)
                and TIME_RE.match(self.closes)):
            raise ValueError("an open day needs opens and closes as HH:MM")
        return self


@router.get("/topics")
def get_topics(request: Request, conn: psycopg.Connection = Depends(get_conn)) -> list[dict]:
    """What visitors are asking, clustered. Folds new log rows in on each call."""
    return topics.topics(conn, request.app.state.settings)


@router.get("/gaps")
def get_gaps(request: Request, state: Literal["open", "asked", "answered"] = "open",
             conn: psycopg.Connection = Depends(get_conn)) -> list[dict]:
    return topics.gaps(conn, request.app.state.settings, state)


@router.post("/gaps/{gap_id}/asked")
def gap_asked(gap_id: str, request: Request,
              conn: psycopg.Connection = Depends(get_conn)) -> JSONResponse:
    """Mark a gap `asked`. Only one gap is `asked` at a time."""
    return run(request, conn, lambda: topics.mark_asked(conn, request.app.state.settings,
                                                        gap_id))


@router.post("/answers")
def post_answer(body: AnswerBody, request: Request,
                conn: psycopg.Connection = Depends(get_conn)) -> JSONResponse:
    """The owner's exact words become a verified FAQ. Accepted only for a gap in `asked`."""
    return run(request, conn, lambda: owner_words.answer(
        conn, request.app.state.settings, body.gap_id, body.answer_text))


@router.post("/special-hours")
def post_special_hours(body: SpecialHoursBody, request: Request,
                       conn: psycopg.Connection = Depends(get_conn)) -> JSONResponse:
    """An owner-verified SpecialHours node from an owner message."""
    return run(request, conn, lambda: owner_words.special_hours(
        conn, request.app.state.settings, body.model_dump()))


@router.post("/publish")
def post_publish(request: Request, conn: psycopg.Connection = Depends(get_conn)) -> JSONResponse:
    """Publish, then replay the top logged intents and the demo list to warm the cache."""
    return run(request, conn, lambda: {
        "graph_version": publisher.publish_now(conn, request.app.state.settings)})
