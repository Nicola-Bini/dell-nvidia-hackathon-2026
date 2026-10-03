import { useId, useState, type FormEvent, type ReactNode } from "react";
import type { ActionResult, FieldError } from "../types";
import type { SurfaceContext } from "./types";
import "./forms.css";

export type FieldErrors = Record<string, string>;

export interface FieldProps {
  name: string;
  label: string;
  type?: string;
  required?: boolean;
  defaultValue?: string | number;
  options?: string[];
  min?: number;
  max?: number;
  error?: string;
  textarea?: boolean;
}

export function Field(p: FieldProps) {
  const id = useId();
  const errId = `${id}-err`;
  const common = {
    id,
    name: p.name,
    required: p.required,
    defaultValue: p.defaultValue,
    "aria-invalid": p.error ? true : undefined,
    "aria-describedby": p.error ? errId : undefined,
  };
  let control: ReactNode;
  if (p.options) {
    control = (
      <select {...common}>
        <option value=""></option>
        {p.options.map((o) => (
          <option key={o} value={o}>
            {o}
          </option>
        ))}
      </select>
    );
  } else if (p.textarea) {
    control = <textarea {...common} rows={3} />;
  } else {
    control = <input {...common} type={p.type ?? "text"} min={p.min} max={p.max} />;
  }
  return (
    <div className="cac-field">
      <label htmlFor={id}>{p.label}</label>
      {control}
      {p.error ? (
        <span id={errId} role="alert" className="cac-field-error">
          {p.error}
        </span>
      ) : null}
    </div>
  );
}

function toErrors(list: FieldError[] | undefined): FieldErrors {
  const out: FieldErrors = {};
  for (const e of list ?? []) {
    out[e.field] = out[e.field] ? `${out[e.field]} ${e.message}` : e.message;
  }
  return out;
}

export function readValues(form: HTMLFormElement): Record<string, string> {
  const out: Record<string, string> = {};
  new FormData(form).forEach((v, k) => {
    if (typeof v === "string") out[k] = v;
  });
  return out;
}

/** Shared submit state. `known` lists field names; other error fields show at the top. */
export function useSubmit(
  ctx: SurfaceContext,
  known: string[],
  send: (values: Record<string, string>) => Promise<ActionResult>,
) {
  const [busy, setBusy] = useState(false);
  const [errors, setErrors] = useState<FieldErrors>({});
  const [notice, setNotice] = useState("");
  const [sent, setSent] = useState(false);

  const onSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const values = readValues(e.currentTarget);
    setBusy(true);
    setErrors({});
    setNotice("");
    try {
      const r = await send(values);
      if (r.ok) setSent(true);
      else setErrors(toErrors(r.errors));
    } catch {
      setNotice("Could not send. Please try again.");
    } finally {
      setBusy(false);
    }
  };

  const topErrors = Object.entries(errors)
    .filter(([f]) => !known.includes(f))
    .map(([, m]) => m);
  return { busy, errors, notice, sent, topErrors, onSubmit, ctx };
}

export function FormStatus(p: { notice: string; topErrors: string[]; sent: boolean }) {
  return (
    <>
      {p.topErrors.map((m, i) => (
        <p key={i} role="alert" className="cac-field-error">
          {m}
        </p>
      ))}
      {p.notice ? (
        <p role="alert" className="cac-field-error">
          {p.notice}
        </p>
      ) : null}
      {p.sent ? (
        <p role="status" className="cac-form-ok">
          Request sent.
        </p>
      ) : null}
    </>
  );
}

export function str(v: unknown): string | undefined {
  return typeof v === "string" || typeof v === "number" ? String(v) : undefined;
}
