const configuredApiUrl = import.meta.env.VITE_API_URL?.replace(/\/$/, "");
export const API_BASE_URL = configuredApiUrl
  ? configuredApiUrl.endsWith("/api")
    ? configuredApiUrl
    : `${configuredApiUrl}/api`
  : "/api";

/** An API error carrying the server's human-readable `detail` message when it sent one. */
export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function apiError(res: Response, fallback: string): Promise<ApiError> {
  try {
    const body = await res.json();
    if (typeof body?.detail === "string") return new ApiError(res.status, body.detail);
  } catch {
    // not JSON
  }
  return new ApiError(res.status, `${fallback} (HTTP ${res.status})`);
}

// Called when a request that needs a session gets 401 (e.g. the session expired),
// so the app can return to the sign-in screen.
let unauthorizedHandler: (() => void) | null = null;

export function setUnauthorizedHandler(handler: (() => void) | null): void {
  unauthorizedHandler = handler;
}

/** fetch() for routes that need the session cookie. */
export async function authFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const res = await fetch(`${API_BASE_URL}${path}`, { ...init, credentials: "include" });
  if (res.status === 401) unauthorizedHandler?.();
  return res;
}

// --- health -----------------------------------------------------------------------

export interface Health {
  status: string;
  model_fast: string;
  model_heavy: string;
  embedding_model: string;
  web_backend: string;
  langsmith_tracing: boolean;
  allow_registration: boolean;
}

export async function fetchHealth(): Promise<Health> {
  const res = await fetch(`${API_BASE_URL}/health`, { credentials: "include" });
  if (!res.ok) throw new Error(`health ${res.status}`);
  return res.json();
}

// --- auth -------------------------------------------------------------------------

export interface SessionUser {
  username: string;
}

/** The signed-in user, or null when there is no valid session (or the server is unreachable). */
export async function getSession(): Promise<SessionUser | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/auth/session`, { credentials: "include" });
    if (!res.ok) return null;
    const body = await res.json();
    return body.user as SessionUser;
  } catch {
    return null;
  }
}

async function postCredentials(
  path: "login" | "register",
  username: string,
  password: string,
): Promise<SessionUser> {
  const res = await fetch(`${API_BASE_URL}/auth/${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ username, password }),
  });
  if (path === "register" && res.status === 404) {
    // A backend without the account routes (e.g. an older version still deployed).
    throw new ApiError(404, "Account creation is not available on the server yet. Try again shortly.");
  }
  if (!res.ok) {
    throw await apiError(res, path === "login" ? "Sign-in failed" : "Registration failed");
  }
  const body = await res.json();
  return body.user as SessionUser;
}

export function login(username: string, password: string): Promise<SessionUser> {
  return postCredentials("login", username, password);
}

export function register(username: string, password: string): Promise<SessionUser> {
  return postCredentials("register", username, password);
}

export async function logout(): Promise<void> {
  await fetch(`${API_BASE_URL}/auth/logout`, { method: "POST", credentials: "include" });
}

// --- documents --------------------------------------------------------------------

export interface IngestResult {
  chunks_added: number;
  files: string[];
}

export async function uploadDocuments(files: File[]): Promise<IngestResult> {
  const form = new FormData();
  for (const f of files) form.append("files", f);
  const res = await authFetch("/ingest", { method: "POST", body: form });
  if (!res.ok) throw await apiError(res, "Upload failed");
  return res.json();
}

export interface DocumentInfo {
  id: string;
  name: string;
  chunks: number;
  uploaded_at: number | null;
}

export interface DocumentList {
  documents: DocumentInfo[];
  total_chunks: number;
}

export async function listDocuments(): Promise<DocumentList> {
  const res = await authFetch("/documents");
  if (!res.ok) throw await apiError(res, "Could not load your documents");
  return res.json();
}

export async function deleteDocument(id: string): Promise<void> {
  const res = await authFetch(`/documents/${encodeURIComponent(id)}`, { method: "DELETE" });
  if (!res.ok) throw await apiError(res, "Could not delete the document");
}
