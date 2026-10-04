import { useCallback, useEffect, useState } from "react";
import { Database, Activity } from "lucide-react";
import { useAgentStream } from "@/hooks/useAgentStream";
import {
  fetchHealth,
  getSession,
  listDocuments,
  logout,
  setUnauthorizedHandler,
  type DocumentList,
  type Health,
  type SessionUser,
} from "@/lib/api";
import { AuthGate } from "@/components/AuthGate";
import { AppShell } from "@/components/layout/AppShell";
import { ChatPanel } from "@/components/chat/ChatPanel";
import { ActivityTimeline } from "@/components/agent/ActivityTimeline";
import { SourcesPanel } from "@/components/sources/SourcesPanel";

function HealthBadge({ health, library }: { health: Health | null; library: DocumentList | null }) {
  if (!health) return null;
  const docs = library?.documents.length ?? 0;
  return (
    <div className="hidden items-center gap-3 rounded-lg border border-border bg-surface px-3 py-1.5 text-xs text-muted sm:flex">
      <span className="inline-flex items-center gap-1" title="Documents in your private library">
        <Database className="h-3.5 w-3.5" />
        {docs} {docs === 1 ? "doc" : "docs"}
      </span>
      <span className="inline-flex items-center gap-1">
        <Activity className="h-3.5 w-3.5" />
        {health.web_backend}
      </span>
      {health.langsmith_tracing && (
        <span className="rounded bg-ok/15 px-1.5 py-0.5 text-ok">tracing on</span>
      )}
    </div>
  );
}

/** Everything a signed-in user sees. Remounted per user, so no state leaks between accounts. */
function Workspace({ user, onLogout }: { user: SessionUser; onLogout: () => void }) {
  const stream = useAgentStream();
  const [health, setHealth] = useState<Health | null>(null);
  const [library, setLibrary] = useState<DocumentList | null>(null);

  const refreshLibrary = useCallback(() => {
    listDocuments().then(setLibrary).catch(() => {});
  }, []);

  useEffect(() => {
    fetchHealth().then(setHealth).catch(() => {});
    refreshLibrary();
  }, [refreshLibrary]);

  return (
    <AppShell
      username={user.username}
      onLogout={onLogout}
      health={<HealthBadge health={health} library={library} />}
      documents={library?.documents ?? []}
      onDocumentsChanged={refreshLibrary}
      chat={<ChatPanel stream={stream} />}
      inspector={
        <>
          <ActivityTimeline timeline={stream.timeline} streaming={stream.status === "streaming"} />
          <SourcesPanel sources={stream.sources} />
        </>
      }
    />
  );
}

export default function App() {
  // undefined = still checking the session, null = signed out
  const [user, setUser] = useState<SessionUser | null | undefined>(undefined);

  useEffect(() => {
    getSession().then(setUser);
    setUnauthorizedHandler(() => setUser(null));
    return () => setUnauthorizedHandler(null);
  }, []);

  const handleLogout = useCallback(async () => {
    try {
      await logout();
    } catch {
      // the session cookie may already be gone; signing out locally is what matters
    }
    setUser(null);
  }, []);

  if (user === undefined) return null;
  if (user === null) return <AuthGate onAuthenticated={setUser} />;
  return <Workspace key={user.username} user={user} onLogout={handleLogout} />;
}
