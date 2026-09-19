import { useState, type FormEvent } from "react";
import { login } from "@/lib/api";

export function AuthGate({ onAuthenticated }: { onAuthenticated: () => void }) {
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    try {
      await login(password);
      onAuthenticated();
    } catch {
      setError("Invalid password.");
    }
  };

  return (
    <main className="flex h-full items-center justify-center bg-bg p-4">
      <form onSubmit={submit} className="w-full max-w-sm rounded-xl border border-border bg-surface p-6 shadow-xl">
        <h1 className="mb-1 text-lg font-semibold">Agentic RAG Assistant</h1>
        <p className="mb-5 text-sm text-muted">Sign in to access your private document collection.</p>
        <label className="mb-2 block text-sm font-medium" htmlFor="password">Password</label>
        <input
          id="password"
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          className="mb-3 w-full rounded-lg border border-border bg-bg px-3 py-2"
          autoFocus
        />
        {error && <p className="mb-3 text-sm text-danger">{error}</p>}
        <button type="submit" className="w-full rounded-lg bg-accent px-3 py-2 text-sm font-medium text-white">
          Sign in
        </button>
      </form>
    </main>
  );
}
