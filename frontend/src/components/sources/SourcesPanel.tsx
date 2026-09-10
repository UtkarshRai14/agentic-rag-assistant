import { BookMarked } from "lucide-react";
import type { Source } from "@/lib/events";
import { SourceCard } from "./SourceCard";

export function SourcesPanel({ sources }: { sources: Source[] }) {
  return (
    <section className="rounded-xl border border-border bg-surface p-4">
      <header className="mb-3 flex items-center gap-2">
        <BookMarked className="h-4 w-4 text-accent" />
        <h2 className="text-sm font-semibold">Sources</h2>
        {sources.length > 0 && (
          <span className="ml-auto rounded-full bg-surface-2 px-2 py-0.5 text-xs text-muted">
            {sources.length}
          </span>
        )}
      </header>

      {sources.length === 0 ? (
        <p className="text-xs text-muted">Retrieved documents and web results show up here.</p>
      ) : (
        <div className="flex flex-col gap-2">
          {sources.map((s, i) => (
            <SourceCard key={s.id} source={s} index={i + 1} />
          ))}
        </div>
      )}
    </section>
  );
}
