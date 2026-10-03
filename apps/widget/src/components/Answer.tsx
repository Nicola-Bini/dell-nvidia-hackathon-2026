import "./content.css";
import type { ComponentProps } from "./types";

interface AnswerData {
  question?: string;
  answer?: string;
  verified?: boolean;
  verified_at?: string | null;
}

export function Answer({ data }: ComponentProps<AnswerData>) {
  const { question, answer, verified, verified_at } = data ?? {};
  return (
    <section className="cac-card cac-answer" data-component="Answer">
      {question ? <h2 className="cac-card-title">{question}</h2> : null}
      {answer ? <p className="cac-answer-text">{answer}</p> : null}
      {verified ? (
        <p className="cac-verified-note">
          {"✓ Confirmed by the restaurant"}
          {verified_at ? ` (${verified_at})` : ""}
        </p>
      ) : null}
    </section>
  );
}
