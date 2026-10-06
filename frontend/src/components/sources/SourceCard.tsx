import { FileText, Globe, ExternalLink } from "lucide-react";
import type { Source } from "@/lib/events";

export function SourceCard({ source }: { source: Source }) {
  const Icon = source.kind === "web" ? Globe : FileText;
  return (
    <article
      id={`source-idx-${source.number}`}
      className="scroll-mt-4 rounded-lg border border-border bg-surface-2 p-3 transition-shadow"
    >
      <div className="flex items-start gap-2">
        <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-accent text-[11px] font-semibold text-accent-fg">
          {source.number}
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5">
            <Icon className="h-3.5 w-3.5 shrink-0 text-muted" />
            {source.url ? (
              <a
                href={source.url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 truncate text-sm font-medium text-accent hover:underline"
              >
                <span className="truncate">{source.title}</span>
                <ExternalLink className="h-3 w-3 shrink-0" />
              </a>
            ) : (
              <span className="truncate text-sm font-medium">{source.title}</span>
            )}
          </div>
          <p className="mt-1 line-clamp-3 text-xs text-muted">{source.snippet}</p>
        </div>
      </div>
    </article>
  );
}
