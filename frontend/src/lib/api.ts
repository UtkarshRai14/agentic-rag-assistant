const configuredApiUrl = import.meta.env.VITE_API_URL?.replace(/\/$/, "");
export const API_BASE_URL = configuredApiUrl
  ? configuredApiUrl.endsWith("/api")
    ? configuredApiUrl
    : `${configuredApiUrl}/api`
  : "/api";

export interface Health {
  status: string;
  model_fast: string;
  model_heavy: string;
  embedding_model: string;
  web_backend: string;
  langsmith_tracing: boolean;
  documents_indexed: number;
}

export async function fetchHealth(): Promise<Health> {
  const res = await fetch(`${API_BASE_URL}/health`, { credentials: "include" });
  if (!res.ok) throw new Error(`health ${res.status}`);
  return res.json();
}

export interface IngestResult {
  chunks_added: number;
  files: string[];
}

export async function uploadDocuments(files: File[]): Promise<IngestResult> {
  const form = new FormData();
  for (const f of files) form.append("files", f);
  const res = await fetch(`${API_BASE_URL}/ingest`, {
    method: "POST",
    body: form,
    credentials: "include",
  });
  if (!res.ok) throw new Error(`ingest ${res.status}`);
  return res.json();
}

export async function checkSession(): Promise<boolean> {
  const res = await fetch(`${API_BASE_URL}/auth/session`, { credentials: "include" });
  return res.ok;
}

export async function login(password: string): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ password }),
  });
  if (!res.ok) throw new Error("Invalid password");
}
