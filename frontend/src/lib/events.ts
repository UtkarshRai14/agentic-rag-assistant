// SSE event contract — mirrors src/rag_agent/streaming.py

export type StepStatus = "running" | "done" | "error";

export interface Source {
  id: string;
  kind: "document" | "web";
  title: string;
  url?: string;
  snippet: string;
  score?: number | null;
}

export type AgentEvent =
  | { type: "start"; thread_id: string }
  | { type: "token"; thread_id: string; delta: string; node?: string }
  | { type: "tool_start"; thread_id: string; id: string; tool: string; args?: unknown }
  | {
      type: "tool_end";
      thread_id: string;
      id: string;
      tool: string;
      ok: boolean;
      result_preview?: string;
    }
  | { type: "sources"; thread_id: string; tool: string; sources: Source[] }
  | { type: "error"; thread_id: string; message: string; fatal?: boolean }
  | { type: "end"; thread_id: string };
