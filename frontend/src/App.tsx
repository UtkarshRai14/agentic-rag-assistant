import { useEffect, useState } from "react";
import { Database, Activity } from "lucide-react";
import { useAgentStream } from "@/hooks/useAgentStream";
import { fetchHealth, type Health } from "@/lib/api";
import { AppShell } from "@/components/layout/AppShell";
import { ChatPanel } from "@/components/chat/ChatPanel";
import { ActivityTimeline } from "@/components/agent/ActivityTimeline";
import { SourcesPanel } from "@/components/sources/SourcesPanel";

function HealthBadge({ health }: { health: Health | null }) {
  if (!health) return null;
  return (
    <div className="hidden items-center gap-3 rounded-lg border border-border bg-surface px-3 py-1.5 text-xs text-muted sm:flex">
      <span className="inline-flex items-center gap-1">
        <Database className="h-3.5 w-3.5" />
        {health.documents_indexed} chunks
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

export default function App() {
  const stream = useAgentStream();
  const [health, setHealth] = useState<Health | null>(null);

  const refreshHealth = () => fetchHealth().then(setHealth).catch(() => {});
  useEffect(() => {
    refreshHealth();
  }, []);

  return (
    <AppShell
      health={<HealthBadge health={health} />}
      onIngested={refreshHealth}
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
