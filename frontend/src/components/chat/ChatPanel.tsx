import { AlertTriangle } from "lucide-react";
import type { useAgentStream } from "@/hooks/useAgentStream";
import { MessageList } from "./MessageList";
import { Composer } from "./Composer";

type Stream = ReturnType<typeof useAgentStream>;

export function ChatPanel({ stream }: { stream: Stream }) {
  const streaming = stream.status === "streaming";
  return (
    <div className="flex h-full flex-col">
      <MessageList
        messages={stream.messages}
        liveAnswer={stream.answer}
        streaming={streaming}
      />
      {stream.error && (
        <div className="mx-auto flex max-w-3xl items-center gap-2 px-4 pb-2 text-xs text-danger">
          <AlertTriangle className="h-3.5 w-3.5" />
          {stream.error}
        </div>
      )}
      <Composer onSend={stream.send} onStop={stream.stop} streaming={streaming} />
    </div>
  );
}
