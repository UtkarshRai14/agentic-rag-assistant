import { useCallback, useReducer, useRef } from "react";
import { parseSSEStream } from "@/lib/sse";
import type { AgentEvent, Source, StepStatus } from "@/lib/events";

export interface TimelineNode {
  id: string;
  tool: string;
  status: StepStatus;
  detail?: string;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

interface StreamState {
  status: "idle" | "streaming" | "done" | "error";
  messages: ChatMessage[];
  answer: string; // live, in-progress assistant text
  timeline: TimelineNode[];
  sources: Source[];
  error?: string;
  threadId?: string;
}

const initial: StreamState = {
  status: "idle",
  messages: [],
  answer: "",
  timeline: [],
  sources: [],
};

type Action =
  | { kind: "user"; text: string }
  | { kind: "event"; event: AgentEvent }
  | { kind: "abort" };

function reducer(s: StreamState, a: Action): StreamState {
  if (a.kind === "user") {
    return {
      ...s,
      status: "streaming",
      messages: [...s.messages, { role: "user", content: a.text }],
      answer: "",
      timeline: [],
      sources: [],
      error: undefined,
    };
  }

  if (a.kind === "abort") {
    // commit whatever we have as a finished message
    const msgs = s.answer
      ? [...s.messages, { role: "assistant" as const, content: s.answer }]
      : s.messages;
    return { ...s, status: "idle", messages: msgs, answer: "" };
  }

  const e = a.event;
  switch (e.type) {
    case "start":
      return { ...s, threadId: e.thread_id };
    case "token":
      return { ...s, status: "streaming", answer: s.answer + e.delta };
    case "tool_start": {
      const node: TimelineNode = { id: e.id, tool: e.tool, status: "running" };
      const i = s.timeline.findIndex((n) => n.id === e.id);
      const timeline =
        i === -1 ? [...s.timeline, node] : s.timeline.map((n) => (n.id === e.id ? node : n));
      return { ...s, timeline };
    }
    case "tool_end":
      return {
        ...s,
        timeline: s.timeline.map((n) =>
          n.id === e.id
            ? { ...n, status: e.ok ? "done" : "error", detail: e.result_preview }
            : n,
        ),
      };
    case "sources": {
      // de-dup by id
      const seen = new Set(s.sources.map((x) => x.id));
      const fresh = e.sources.filter((x) => !seen.has(x.id));
      return { ...s, sources: [...s.sources, ...fresh] };
    }
    case "error":
      return { ...s, status: e.fatal ? "error" : s.status, error: e.message };
    case "end": {
      const msgs = s.answer
        ? [...s.messages, { role: "assistant" as const, content: s.answer }]
        : s.messages;
      return { ...s, status: "done", messages: msgs, answer: "" };
    }
    default:
      return s;
  }
}

export function useAgentStream() {
  const [state, dispatch] = useReducer(reducer, initial);
  const abortRef = useRef<AbortController | null>(null);
  const threadRef = useRef<string | undefined>(undefined);

  const send = useCallback(async (message: string) => {
    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;
    dispatch({ kind: "user", text: message });

    try {
      const res = await fetch("/api/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
        body: JSON.stringify({ message, thread_id: threadRef.current }),
        signal: ac.signal,
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      for await (const ev of parseSSEStream(res, ac.signal)) {
        if (ev.type === "start") threadRef.current = ev.thread_id;
        dispatch({ kind: "event", event: ev });
      }
    } catch (err) {
      if ((err as Error).name !== "AbortError") {
        dispatch({
          kind: "event",
          event: { type: "error", thread_id: "", message: String(err), fatal: true },
        });
      }
    }
  }, []);

  const stop = useCallback(() => {
    abortRef.current?.abort();
    dispatch({ kind: "abort" });
  }, []);

  return { ...state, send, stop };
}
