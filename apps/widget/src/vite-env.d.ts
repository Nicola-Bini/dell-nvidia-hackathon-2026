/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Serve API origin (http://127.0.0.1:8080), "same-origin", or "mock". See transport/index.ts. */
  readonly VITE_SERVE_URL?: string;
}
