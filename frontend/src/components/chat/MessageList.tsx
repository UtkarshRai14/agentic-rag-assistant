import { useEffect, useRef } from "react";
import { Sparkles } from "lucide-react";
import type { ChatMessage } from "@/hooks/useAgentStream";
import { MessageBubble } from "./MessageBubble";

export function MessageList({
  messages,
  liveAnswer,
  streaming,
}: {
  messages: ChatMessage[];
  liveAnswer: string;
  streaming: boolean;
}) {
  const endRef = useRef<HTMLDivElement>(null);
  const atBottomRef = useRef(true);

  useEffect(() => {
    if (atBottomRef.current) endRef.current?.scrollIntoView({ block: "end" });
  }, [messages, liveAnswer, streaming]);

  const onScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const el = e.currentTarget;
    atBottomRef.current = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
  };

  const empty = messages.length === 0 && !liveAnswer;

  return (
    <div onScroll={onScroll} className="flex-1 overflow-y-auto px-4 py-6">
      {empty ? (
        <div className="mx-auto mt-16 max-w-md text-center">
          <Sparkles className="mx-auto mb-3 h-8 w-8 text-accent" />
          <h2 className="text-lg font-semibold">Ask the research agent</h2>
          <p className="mt-2 text-sm text-muted">
            It searches your uploaded documents and the web, then answers with
            citations. Try asking about the Aurora platform, or upload your own docs.
          </p>
        </div>
      ) : (
        <div className="mx-auto flex max-w-3xl flex-col gap-5">
          {messages.map((m, i) => (
            <MessageBubble key={i} role={m.role} content={m.content} />
          ))}
          {liveAnswer && <MessageBubble role="assistant" content={liveAnswer} streaming />}
          {streaming && !liveAnswer && (
            <MessageBubble role="assistant" content="" streaming />
          )}
          <div ref={endRef} />
        </div>
      )}
    </div>
  );
}
