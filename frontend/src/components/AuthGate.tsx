import { useEffect, useState, type FormEvent } from "react";
import { Loader2 } from "lucide-react";
import { fetchHealth, login, register, type SessionUser } from "@/lib/api";
import { cn } from "@/lib/utils";

type Mode = "signin" | "register";

export function AuthGate({ onAuthenticated }: { onAuthenticated: (user: SessionUser) => void }) {
  const [mode, setMode] = useState<Mode>("signin");
  const [registrationOpen, setRegistrationOpen] = useState(false);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    fetchHealth()
      .then((health) => setRegistrationOpen(health.allow_registration))
      .catch(() => setRegistrationOpen(false));
  }, []);

  const switchMode = (next: Mode) => {
    setMode(next);
    setError(null);
    setPassword("");
    setConfirm("");
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    if (mode === "register" && password !== confirm) {
      setError("Passwords do not match.");
      return;
    }
    setBusy(true);
    try {
      const user =
        mode === "signin" ? await login(username, password) : await register(username, password);
      onAuthenticated(user);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setBusy(false);
    }
  };

  const registering = mode === "register";

  return (
    <main className="flex h-full items-center justify-center bg-bg p-4">
      <form
        onSubmit={submit}
        className="w-full max-w-sm rounded-xl border border-border bg-surface p-6 shadow-xl"
      >
        <h1 className="mb-1 text-lg font-semibold">Agentic RAG Assistant</h1>
        <p className="mb-5 text-sm text-muted">
          {registering
            ? "Create an account. The documents you upload are private to your account."
            : "Sign in to access your private document collection."}
        </p>

        {registrationOpen && (
          <div className="mb-5 grid grid-cols-2 gap-1 rounded-lg bg-surface-2 p-1 text-sm">
            {(["signin", "register"] as const).map((m) => (
              <button
                key={m}
                type="button"
                onClick={() => switchMode(m)}
                className={cn(
                  "rounded-md px-3 py-1.5",
                  mode === m ? "bg-surface font-medium shadow-sm" : "text-muted hover:text-fg",
                )}
              >
                {m === "signin" ? "Sign in" : "Create account"}
              </button>
            ))}
          </div>
        )}

        <label className="mb-2 block text-sm font-medium" htmlFor="username">
          Username
        </label>
        <input
          id="username"
          type="text"
          value={username}
          onChange={(event) => setUsername(event.target.value)}
          className="mb-3 w-full rounded-lg border border-border bg-bg px-3 py-2"
          autoComplete="username"
          autoCapitalize="none"
          spellCheck={false}
          maxLength={registering ? 32 : 64}
          required
          autoFocus
        />
        {registering && (
          <p className="-mt-2 mb-3 text-xs text-muted">
            3-32 characters: letters, numbers, dots, dashes or underscores.
          </p>
        )}

        <label className="mb-2 block text-sm font-medium" htmlFor="password">
          Password
        </label>
        <input
          id="password"
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          className="mb-3 w-full rounded-lg border border-border bg-bg px-3 py-2"
          autoComplete={registering ? "new-password" : "current-password"}
          minLength={registering ? 8 : undefined}
          maxLength={128}
          required
        />

        {registering && (
          <>
            <label className="mb-2 block text-sm font-medium" htmlFor="confirm">
              Repeat password
            </label>
            <input
              id="confirm"
              type="password"
              value={confirm}
              onChange={(event) => setConfirm(event.target.value)}
              className="mb-3 w-full rounded-lg border border-border bg-bg px-3 py-2"
              autoComplete="new-password"
              minLength={8}
              maxLength={128}
              required
            />
          </>
        )}

        {error && <p className="mb-3 text-sm text-danger">{error}</p>}
        <button
          type="submit"
          disabled={busy}
          className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-accent px-3 py-2 text-sm font-medium text-accent-fg disabled:opacity-60"
        >
          {busy && <Loader2 className="h-4 w-4 animate-spin" />}
          {registering ? "Create account" : "Sign in"}
        </button>
      </form>
    </main>
  );
}
