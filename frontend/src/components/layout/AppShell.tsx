import type { ReactNode } from "react";
import { LogOut, UserRound } from "lucide-react";
import type { DocumentInfo } from "@/lib/api";
import { ThemeToggle } from "./ThemeToggle";
import { UploadDialog } from "@/components/upload/UploadDialog";

export function AppShell({
  username,
  onLogout,
  health,
  documents,
  onDocumentsChanged,
  chat,
  inspector,
}: {
  username: string;
  onLogout: () => void;
  health?: ReactNode;
  documents: DocumentInfo[];
  onDocumentsChanged: () => void;
  chat: ReactNode;
  inspector: ReactNode;
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
          <UploadDialog documents={documents} onChanged={onDocumentsChanged} />
          <ThemeToggle />
          <span
            className="hidden max-w-[10rem] items-center gap-1 truncate text-sm text-muted md:inline-flex"
            title={`Signed in as ${username}`}
          >
            <UserRound className="h-4 w-4 shrink-0" />
            <span className="truncate">{username}</span>
          </span>
          <button
            onClick={onLogout}
            className="flex h-9 w-9 items-center justify-center rounded-lg border border-border bg-surface text-muted hover:text-fg"
            title="Sign out"
            aria-label="Sign out"
          >
            <LogOut className="h-4 w-4" />
          </button>
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
