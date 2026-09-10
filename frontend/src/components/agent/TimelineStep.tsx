import { Check, X, Loader2 } from "lucide-react";
import type { TimelineNode } from "@/hooks/useAgentStream";
import { StepIcon, toolLabel } from "./stepIcons";
import { cn } from "@/lib/utils";

export function TimelineStep({ node, last }: { node: TimelineNode; last: boolean }) {
  return (
    <li className="step-enter relative flex gap-3 pb-4">
      {!last && (
        <span className="absolute left-[15px] top-8 h-[calc(100%-1.5rem)] w-px bg-border" />
      )}
      <span
        className={cn(
          "flex h-8 w-8 shrink-0 items-center justify-center rounded-full border",
          node.status === "running" && "border-accent text-accent",
          node.status === "done" && "border-ok/40 text-ok bg-ok/10",
          node.status === "error" && "border-danger/40 text-danger bg-danger/10",
        )}
      >
        <StepIcon tool={node.tool} className={cn("h-4 w-4", node.status === "running" && "pulse")} />
      </span>

      <div className="min-w-0 flex-1 pt-1">
        <div className="flex items-center gap-2">
          <span className="truncate text-sm font-medium">{toolLabel(node.tool)}</span>
          {node.status === "running" && <Loader2 className="h-3.5 w-3.5 animate-spin text-muted" />}
          {node.status === "done" && <Check className="h-3.5 w-3.5 text-ok" />}
          {node.status === "error" && <X className="h-3.5 w-3.5 text-danger" />}
        </div>
        {node.detail && (
          <p className="mt-0.5 line-clamp-2 text-xs text-muted">{node.detail}</p>
        )}
      </div>
    </li>
  );
}
