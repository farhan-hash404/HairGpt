"use client";

import * as React from "react";
import { Lock, ShieldCheck } from "lucide-react";
import { api, clearTokens, getToken } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const REQUIRED_CONSENTS = [
  { purpose: "storage", label: "Store my photos securely (encrypted)" },
  { purpose: "analysis", label: "Analyze my photos to produce observations" },
];
const OPTIONAL_CONSENTS = [
  { purpose: "longitudinal", label: "Keep photos to compare over time" },
  { purpose: "research_optin", label: "Optional: contribute de-identified data to research" },
];

/** Wraps pages that need auth + consent. Consent is required BEFORE any analysis. */
export function AuthGate({ children }: { children: React.ReactNode }) {
  const [state, setState] = React.useState<"loading" | "anon" | "consent" | "ready">("loading");
  const [consents, setConsents] = React.useState<Record<string, boolean>>({});

  const refresh = React.useCallback(async () => {
    if (!getToken()) return setState("anon");
    try {
      const me = await api.me();
      const map: Record<string, boolean> = {};
      me.consents.forEach((c: any) => (map[c.purpose] = c.granted));
      setConsents(map);
      const ok = REQUIRED_CONSENTS.every((c) => map[c.purpose]);
      setState(ok ? "ready" : "consent");
    } catch {
      clearTokens();
      setState("anon");
    }
  }, []);

  React.useEffect(() => {
    refresh();
  }, [refresh]);

  if (state === "loading") return <p className="text-muted-foreground">Loading…</p>;
  if (state === "anon") return <AuthForm onDone={refresh} />;
  if (state === "consent") return <ConsentForm consents={consents} onDone={refresh} />;
  return <>{children}</>;
}

function AuthForm({ onDone }: { onDone: () => void }) {
  const [mode, setMode] = React.useState<"login" | "register">("login");
  const [email, setEmail] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      if (mode === "register") await api.register({ email, password });
      await api.login(email, password);
      onDone();
    } catch (err: any) {
      setError(err?.message ?? "Something went wrong");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-md py-10">
      <Card>
        <CardHeader>
          <div className="mb-1 grid h-10 w-10 place-items-center rounded-xl bg-accent">
            <Lock className="h-4 w-4 text-accent-foreground" />
          </div>
          <CardTitle>{mode === "login" ? "Sign in to HairGPT" : "Create your account"}</CardTitle>
          <p className="text-sm text-muted-foreground">
            Your photos are encrypted, never sold, and never used for facial recognition.
          </p>
        </CardHeader>
        <CardContent>
          <form onSubmit={submit} className="space-y-3">
            <label className="block text-sm">
              <span className="mb-1 block font-medium">Email</span>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-xl border bg-background px-3 py-2 outline-none focus-visible:ring-2 focus-visible:ring-ring"
              />
            </label>
            <label className="block text-sm">
              <span className="mb-1 block font-medium">Password</span>
              <input
                type="password"
                required
                minLength={8}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-xl border bg-background px-3 py-2 outline-none focus-visible:ring-2 focus-visible:ring-ring"
              />
            </label>
            {error && <p className="text-sm text-destructive">{error}</p>}
            <Button type="submit" disabled={busy} className="w-full">
              {busy ? "Please wait…" : mode === "login" ? "Sign in" : "Create account"}
            </Button>
          </form>
          <button
            onClick={() => setMode(mode === "login" ? "register" : "login")}
            className="mt-4 w-full text-sm text-muted-foreground hover:text-foreground"
          >
            {mode === "login" ? "New here? Create an account" : "Already have an account? Sign in"}
          </button>
        </CardContent>
      </Card>
    </div>
  );
}

function ConsentForm({ consents, onDone }: { consents: Record<string, boolean>; onDone: () => void }) {
  const [local, setLocal] = React.useState<Record<string, boolean>>(consents);
  const [busy, setBusy] = React.useState(false);

  async function save() {
    setBusy(true);
    for (const c of [...REQUIRED_CONSENTS, ...OPTIONAL_CONSENTS]) {
      await api.setConsent(c.purpose, !!local[c.purpose]);
    }
    setBusy(false);
    onDone();
  }

  const canProceed = REQUIRED_CONSENTS.every((c) => local[c.purpose]);

  return (
    <div className="mx-auto max-w-lg py-10">
      <Card>
        <CardHeader>
          <div className="mb-1 grid h-10 w-10 place-items-center rounded-xl bg-accent">
            <ShieldCheck className="h-4 w-4 text-accent-foreground" />
          </div>
          <CardTitle>Your consent</CardTitle>
          <p className="text-sm text-muted-foreground">
            Nothing is analyzed until you agree. You can withdraw consent, export, or permanently delete your data at any
            time in Settings.
          </p>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            {REQUIRED_CONSENTS.map((c) => (
              <ConsentRow
                key={c.purpose}
                label={c.label}
                required
                checked={!!local[c.purpose]}
                onChange={(v) => setLocal({ ...local, [c.purpose]: v })}
              />
            ))}
            {OPTIONAL_CONSENTS.map((c) => (
              <ConsentRow
                key={c.purpose}
                label={c.label}
                checked={!!local[c.purpose]}
                onChange={(v) => setLocal({ ...local, [c.purpose]: v })}
              />
            ))}
          </div>
          <ul className="space-y-1 rounded-xl bg-muted/50 p-3 text-xs text-muted-foreground">
            <li>• We never run facial recognition or identity matching.</li>
            <li>• We never sell your images or use them for advertising.</li>
            <li>• Images are encrypted at rest and deletable on request.</li>
          </ul>
          <Button onClick={save} disabled={!canProceed || busy} className="w-full">
            {busy ? "Saving…" : "Agree and continue"}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}

function ConsentRow({
  label,
  checked,
  onChange,
  required,
}: {
  label: string;
  checked: boolean;
  onChange: (v: boolean) => void;
  required?: boolean;
}) {
  return (
    <label className="flex cursor-pointer items-start gap-3 rounded-xl border p-3 text-sm hover:bg-muted/40">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="mt-0.5 h-4 w-4 accent-[hsl(var(--primary))]"
      />
      <span>
        {label}
        {required && <span className="ml-2 text-xs text-muted-foreground">(required)</span>}
      </span>
    </label>
  );
}
