import "./content.css";
import type { ComponentProps } from "./types";

interface WeekRow {
  days?: string[];
  opens?: string | null;
  closes?: string | null;
}
interface HoursData {
  date?: string;
  status?: "open" | "closed" | null;
  opens?: string | null;
  closes?: string | null;
  note?: string | null;
  week?: WeekRow[];
}

const DAY: Record<string, string> = {
  mon: "Mon",
  tue: "Tue",
  wed: "Wed",
  thu: "Thu",
  fri: "Fri",
  sat: "Sat",
  sun: "Sun",
};

function time12(t?: string | null): string {
  const m = /^(\d{1,2}):(\d{2})/.exec(t ?? "");
  if (!m) return "";
  const h = Number(m[1]);
  return `${h % 12 === 0 ? 12 : h % 12}:${m[2]} ${h < 12 ? "AM" : "PM"}`;
}

function range(opens?: string | null, closes?: string | null): string {
  if (!opens || !closes) return "";
  const next = closes < opens ? " (next day)" : "";
  return `${time12(opens)} – ${time12(closes)}${next}`;
}

function dayLabel(days: string[] = []): string {
  const names = days.map((d) => DAY[d] ?? d);
  if (names.length === 0) return "";
  if (names.length === 1) return names[0];
  return `${names[0]}–${names[names.length - 1]}`;
}

export function HoursCard({ data }: ComponentProps<HoursData>) {
  const { date, status, opens, closes, note, week } = data ?? {};
  const today = status === "open" ? range(opens, closes) : "";
  return (
    <section className="cac-card cac-hours" data-component="HoursCard">
      {status ? (
        <p className={`cac-hours-status cac-hours-${status}`}>
          <strong>{status === "open" ? "Open" : "Closed"}</strong>
          {date ? <span className="cac-hours-date">{` ${date}`}</span> : null}
          {today ? <span className="cac-hours-range">{` ${today}`}</span> : null}
        </p>
      ) : null}
      {note ? <p className="cac-hours-note">{note}</p> : null}
      {Array.isArray(week) && week.length > 0 ? (
        <table className="cac-hours-table">
          <tbody>
            {week.map((row, i) => (
              <tr key={i}>
                <th scope="row">{dayLabel(row.days)}</th>
                <td>{range(row.opens, row.closes) || "Closed"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : null}
    </section>
  );
}
