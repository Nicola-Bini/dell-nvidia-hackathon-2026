import { AllergenNotice } from "./AllergenNotice";
import { Answer } from "./Answer";
import { BookingForm } from "./BookingForm";
import { CateringQuoteForm } from "./CateringQuoteForm";
import { FactCard } from "./FactCard";
import { FormCard } from "./FormCard";
import { GoalCTA } from "./GoalCTA";
import { HoursCard } from "./HoursCard";
import { ListCard } from "./ListCard";
import { MenuList } from "./MenuList";
import type { SurfaceComponent } from "./types";

/** SCHEMA 7: the P0 catalog. A component not listed here renders nothing. */
export const registry: Record<string, SurfaceComponent> = {
  Answer,
  MenuList,
  HoursCard,
  BookingForm,
  CateringQuoteForm,
  AllergenNotice,
  GoalCTA,
  FactCard,
  ListCard,
  FormCard,
};
