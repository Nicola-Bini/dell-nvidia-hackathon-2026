const KEY = "cac.session_id";

function uuid(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) return crypto.randomUUID();
  return "s-" + Math.random().toString(36).slice(2) + Date.now().toString(36);
}

/** A UUID kept in sessionStorage; falls back to memory when storage is blocked. */
let memory: string | null = null;
export function sessionId(): string {
  try {
    const found = sessionStorage.getItem(KEY);
    if (found) return found;
    const id = uuid();
    sessionStorage.setItem(KEY, id);
    return id;
  } catch {
    memory ??= uuid();
    return memory;
  }
}
