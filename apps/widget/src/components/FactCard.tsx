import type { ComponentProps } from "./types";
import "./forms.css";

export interface Fact {
  name: string;
  value: string;
}

interface FactData {
  title?: string;
  facts?: Fact[];
  verified?: boolean;
}

const PHONE_RE = /^\+[\d ]+$/;

export function FactValue({ value }: { value: string }) {
  const v = String(value ?? "");
  if (PHONE_RE.test(v.trim())) return <a href={`tel:${v.replace(/\s+/g, "")}`}>{v}</a>;
  return <>{v}</>;
}

export function FactList({ facts }: { facts: Fact[] }) {
  return (
    <dl className="cac-facts">
      {facts.map((f, i) => (
        <div key={i} style={{ display: "contents" }}>
          <dt>{f.name}</dt>
          <dd>
            <FactValue value={f.value} />
          </dd>
        </div>
      ))}
    </dl>
  );
}

export function FactCard({ data }: ComponentProps<FactData>) {
  const facts = Array.isArray(data?.facts) ? data.facts : [];
  return (
    <section className="cac-fact">
      {data?.title ? <h3>{data.title}</h3> : null}
      <FactList facts={facts} />
      {data?.verified ? <p className="cac-verified">Confirmed by the restaurant</p> : null}
    </section>
  );
}
