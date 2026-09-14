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
  const res = await fetch(`${API_BASE_URL}/health`);
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
  const res = await fetch(`${API_BASE_URL}/ingest`, { method: "POST", body: form });
  if (!res.ok) throw new Error(`ingest ${res.status}`);
  return res.json();
}
