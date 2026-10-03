/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Serve API origin, e.g. http://127.0.0.1:8080. Empty: the fixture mock. "same-origin": relative URLs. */
  readonly VITE_SERVE_URL?: string;
}
