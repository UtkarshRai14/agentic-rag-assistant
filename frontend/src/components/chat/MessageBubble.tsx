import { Bot, User } from "lucide-react";
import { cn } from "@/lib/utils";
import { Markdown } from "./Markdown";

export function MessageBubble({
  role,
  content,
  streaming = false,
}: {
  role: "user" | "assistant";
  content: string;
  streaming?: boolean;
}) {
  const isUser = role === "user";
  return (
    <div className={cn("flex gap-3", isUser && "flex-row-reverse")}>
      <span
        className={cn(
          "flex h-8 w-8 shrink-0 items-center justify-center rounded-full",
          isUser ? "bg-surface-2 text-muted" : "bg-accent text-accent-fg",
        )}
      >
        {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
      </span>
      <div
        className={cn(
          "max-w-[78%] rounded-xl px-4 py-2.5",
          isUser ? "bg-accent text-accent-fg" : "border border-border bg-surface",
        )}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap text-sm">{content}</p>
        ) : (
          <>
            <Markdown text={content} highlight={!streaming} />
            {streaming && (
              <span className="ml-0.5 inline-block h-4 w-1.5 translate-y-0.5 animate-pulse rounded-sm bg-accent" />
            )}
          </>
        )}
      </div>
    </div>
  );
}
