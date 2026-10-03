import { Field, FormStatus, str, useSubmit } from "./form";
import type { ComponentProps } from "./types";

interface CateringData {
  prefill?: { headcount?: unknown; date?: unknown };
  min_headcount?: number | null;
}

const KNOWN = ["date", "headcount", "name", "contact", "notes"];

export function CateringQuoteForm({ data, ctx }: ComponentProps<CateringData>) {
  const pre = data?.prefill ?? {};
  const min = typeof data?.min_headcount === "number" ? data.min_headcount : undefined;
  const s = useSubmit(ctx, KNOWN, (v) => {
    const payload: Record<string, unknown> = {
      date: v.date,
      headcount: Number(v.headcount),
      name: v.name,
      contact: v.contact,
    };
    if (v.notes) payload.notes = v.notes;
    return ctx.submit("submit_catering_quote", payload, "CateringQuoteForm");
  });
  const e = s.errors;
  return (
    <form className="cac-form" onSubmit={s.onSubmit} aria-label="Catering quote">
      <h3>Catering quote</h3>
      <Field name="date" label="Event date" type="date" required
        defaultValue={str(pre.date)} error={e.date} />
      <Field
        name="headcount"
        label="Headcount"
        type="number"
        min={min}
        required
        defaultValue={str(pre.headcount)}
        error={e.headcount}
      />
      <Field name="name" label="Name" required error={e.name} />
      <Field name="contact" label="Phone or email" required error={e.contact} />
      <Field name="notes" label="Notes (optional)" textarea error={e.notes} />
      <FormStatus notice={s.notice} topErrors={s.topErrors} sent={s.sent} />
      <button className="cac-btn" type="submit" disabled={s.busy}>
        {s.busy ? "Sending…" : "Request quote"}
      </button>
    </form>
  );
}
