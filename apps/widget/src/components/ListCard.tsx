import { FactList, type Fact } from "./FactCard";
import type { ComponentProps } from "./types";
import "./forms.css";

interface ListData {
  title?: string;
  items?: { id?: string; name?: string; facts?: Fact[] }[];
}

export function ListCard({ data }: ComponentProps<ListData>) {
  const items = Array.isArray(data?.items) ? data.items : [];
  return (
    <section className="cac-list">
      {data?.title ? <h3>{data.title}</h3> : null}
      {items.map((it, i) => (
        <div className="cac-list-item" key={it.id ?? i}>
          <h4>{it.name}</h4>
          <FactList facts={Array.isArray(it.facts) ? it.facts : []} />
        </div>
      ))}
    </section>
  );
}
