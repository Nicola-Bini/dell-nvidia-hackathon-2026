import { Field, FormStatus, useSubmit } from "./form";
import type { ComponentProps } from "./types";

interface FieldCfg {
  name: string;
  type?: string;
  label?: string;
  required?: boolean;
  options?: string[];
}

interface FormData {
  form?: string;
  title?: string;
  fields?: FieldCfg[];
  submit_label?: string;
}

const INPUT_TYPES = ["text", "number", "date"];

export function FormCard({ data, ctx }: ComponentProps<FormData>) {
  const fields = Array.isArray(data?.fields) ? data.fields.filter((f) => f && f.name) : [];
  const formName = data?.form ?? "";
  const s = useSubmit(
    ctx,
    fields.map((f) => f.name),
    (values) => ctx.submit("submit_form", { form: formName, values }, formName),
  );
  return (
    <form className="cac-form" onSubmit={s.onSubmit} aria-label={data?.title || "Form"}>
      {data?.title ? <h3>{data.title}</h3> : null}
      {fields.map((f) => (
        <Field
          key={f.name}
          name={f.name}
          label={f.label || f.name}
          required={!!f.required}
          type={INPUT_TYPES.includes(f.type ?? "") ? f.type : "text"}
          options={f.type === "select" ? (f.options ?? []) : undefined}
          error={s.errors[f.name]}
        />
      ))}
      <FormStatus notice={s.notice} topErrors={s.topErrors} sent={s.sent} />
      <button className="cac-btn" type="submit" disabled={s.busy}>
        {s.busy ? "Sending…" : data?.submit_label || "Send"}
      </button>
    </form>
  );
}
