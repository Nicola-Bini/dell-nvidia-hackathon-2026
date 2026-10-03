import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import { Gallery } from "./Gallery";
import { createTransport } from "./transport";
import "./styles.css";

const root = createRoot(document.getElementById("root") as HTMLElement);
const gallery = location.hash === "#/gallery";
root.render(
  <StrictMode>{gallery ? <Gallery /> : <App transport={createTransport()} />}</StrictMode>,
);
