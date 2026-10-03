import "./content.css";
import type { ComponentProps } from "./types";

interface AllergenData {
  allergen?: string | null;
  contains?: { id: string; name?: string }[];
}

export function AllergenNotice({ view, data }: ComponentProps<AllergenData>) {
  const { allergen, contains } = data ?? {};
  const list = Array.isArray(contains) ? contains : [];
  return (
    <aside className="cac-card cac-allergen" role="note" data-component="AllergenNotice">
      <p className="cac-allergen-text">{view.text}</p>
      {list.length > 0 ? (
        <div className="cac-allergen-list">
          <p>{`Contains ${allergen ?? "this allergen"}:`}</p>
          <ul>
            {list.map((c) => (
              <li key={c.id}>{c.name}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </aside>
  );
}
