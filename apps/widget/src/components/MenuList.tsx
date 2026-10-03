import "./content.css";
import { hasAction, type ComponentProps, type SurfaceContext } from "./types";

interface Badge {
  diet?: string;
  verified?: boolean;
}
interface Item {
  id: string;
  name?: string;
  price?: string;
  description?: string;
  badges?: Badge[];
}
interface MenuData {
  title?: string;
  items?: Item[];
  more?: { label?: string; preset?: string } | null;
}

function BadgeView({ badge }: { badge: Badge }) {
  const diet = badge.diet ?? "";
  if (badge.verified === true) {
    return <span className="cac-badge-verified">{`✓ ${diet} (confirmed)`}</span>;
  }
  return <span className="cac-badge-unverified">{`${diet}: not verified, ask staff`}</span>;
}

function ItemView({ item, canAdd, ctx }: { item: Item; canAdd: boolean; ctx: SurfaceContext }) {
  return (
    <li className="cac-item">
      <div className="cac-item-head">
        <span className="cac-item-name">{item.name}</span>
        {item.price ? <span className="cac-item-price">{item.price}</span> : null}
      </div>
      {item.description ? <p className="cac-item-desc">{item.description}</p> : null}
      <div className="cac-badges">
        {(item.badges ?? []).map((b, i) => (
          <BadgeView key={i} badge={b} />
        ))}
      </div>
      {canAdd ? (
        <button type="button" className="cac-add" onClick={() => ctx.addToCart(item.id)}>
          Add
        </button>
      ) : null}
    </li>
  );
}

export function MenuList({ view, data, ctx }: ComponentProps<MenuData>) {
  const { title, items, more } = data ?? {};
  const canAdd = hasAction(view, "add_to_cart");
  const preset = more?.preset;
  return (
    <section className="cac-card cac-menu" data-component="MenuList">
      {title ? <h2 className="cac-card-title">{title}</h2> : null}
      {Array.isArray(items) ? (
        <ul className="cac-items">
          {items.map((it) => (
            <ItemView key={it.id} item={it} canAdd={canAdd} ctx={ctx} />
          ))}
        </ul>
      ) : null}
      {more && preset ? (
        <button type="button" className="cac-more" onClick={() => ctx.openView(preset)}>
          {more.label}
        </button>
      ) : null}
    </section>
  );
}
