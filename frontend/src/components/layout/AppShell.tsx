import type { ReactNode } from "react";
import { ThemeToggle } from "./ThemeToggle";
import { UploadDialog } from "@/components/upload/UploadDialog";

export function AppShell({
  health,
  chat,
  inspector,
  onIngested,
}: {
  health?: ReactNode;
  chat: ReactNode;
  inspector: ReactNode;
  onIngested?: (chunks: number) => void;
}) {
  return (
    <div className="flex h-full flex-col">
      <header className="flex items-center gap-3 border-b border-border bg-surface/60 px-4 py-2.5 backdrop-blur">
        <img src="/favicon.png" alt="" className="h-6 w-6" />
        <div className="flex flex-col leading-tight">
          <span className="text-sm font-semibold">Agentic RAG Assistant</span>
          <span className="text-[11px] text-muted">LangGraph · LangChain · LangSmith</span>
        </div>
        <div className="ml-auto flex items-center gap-2">
          {health}
          <UploadDialog onIngested={onIngested} />
          <ThemeToggle />
        </div>
      </header>

      <main className="grid min-h-0 flex-1 grid-cols-1 lg:grid-cols-[1fr_360px]">
        <div className="min-h-0 border-r border-border">{chat}</div>
        <aside className="hidden min-h-0 flex-col gap-4 overflow-y-auto bg-bg p-4 lg:flex">
          {inspector}
        </aside>
      </main>
    </div>
  );
}
