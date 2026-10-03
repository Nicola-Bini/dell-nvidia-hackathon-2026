import { install } from "./embed";

// The box is wherever this script was loaded from.
const script = document.currentScript as HTMLScriptElement | null;
const box = script?.src ? new URL(script.src).origin : location.origin;

install({ box }).catch(() => undefined);
