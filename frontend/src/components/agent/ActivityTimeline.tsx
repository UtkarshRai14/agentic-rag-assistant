import { Activity } from "lucide-react";
import type { TimelineNode } from "@/hooks/useAgentStream";
import { TimelineStep } from "./TimelineStep";

export function ActivityTimeline({
  timeline,
  streaming,
}: {
  timeline: TimelineNode[];
  streaming: boolean;
}) {
  return (
    <section className="rounded-xl border border-border bg-surface p-4">
      <header className="mb-3 flex items-center gap-2">
        <Activity className="h-4 w-4 text-accent" />
        <h2 className="text-sm font-semibold">Agent activity</h2>
      </header>

      {timeline.length === 0 ? (
        <p className="text-xs text-muted">
          {streaming ? "Thinking…" : "Steps the agent takes will appear here."}
        </p>
      ) : (
        <ol className="relative">
          {timeline.map((node, i) => (
            <TimelineStep key={node.id} node={node} last={i === timeline.length - 1} />
          ))}
        </ol>
      )}
    </section>
  );
}
