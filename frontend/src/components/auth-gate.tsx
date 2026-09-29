"use client";

import * as React from "react";
import { ShieldCheck } from "lucide-react";
import { api, clearTokens, getToken } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { ReticleMark } from "@/components/wordmark";

const REQUIRED_CONSENTS = [
  { purpose: "storage", label: "Store my photos securely (encrypted)" },
  { purpose: "analysis", label: "Analyze my photos to produce observations" },
];
const OPTIONAL_CONSENTS = [
  { purpose: "longitudinal", label: "Keep photos to compare over time" },
  { purpose: "research_optin", label: "Contribute de-identified data to research" },
];

const PRINCIPLES = [
  {
    title: "It measures",
    body: "Standard views of your scalp, each checked for focus, light and framing before anything is scored.",
  },
  {
    title: "It cites",
    body: "Answers come only from NHS, MedlinePlus, NIAMS, DailyMed and open reviews, verified sentence by sentence.",
  },
  {
    title: "It refers",
    body: "Red flags skip the suggestions entirely and point you to a GP or dermatologist.",
  },
];

const GUARANTEES = [
  "No facial recognition or identity matching, ever.",
  "Images are never sold or used for advertising.",
  "Encrypted at rest; deleted when you ask.",
];

const FIELD =
  "w-full rounded border border-rule-strong bg-surface px-3.5 py-2.5 text-[0.95rem] text-ink placeholder:text-ink-faint focus:border-ink focus:outline-none focus:ring-2 focus:ring-marker/70";

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

  if (state === "loading") {
    return (
      <div className="flex min-h-[40vh] items-center justify-center">
        <div className="flex items-center gap-3 text-ink-soft">
          <ReticleMark className="h-6 w-6 animate-spin text-ink [animation-duration:2.4s]" />
          <p className="label">Connecting to your record…</p>
        </div>
      </div>
    );
  }
  if (state === "anon") return <AuthForm onDone={refresh} />;
  if (state === "consent") return <ConsentForm consents={consents} onDone={refresh} />;
  return <>{children}</>;
}

function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1.5 flex items-baseline justify-between">
        <span className="label text-ink-soft">{label}</span>
        {hint && <span className="caption">{hint}</span>}
      </span>
      {children}
    </label>
  );
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
      const msg =
        err?.message ||
        (typeof err?.detail === "string" ? err.detail : null) ||
        (mode === "login"
          ? "Invalid email or password. Please try again."
          : "Could not create account. Email may already be registered.");
      setError(msg);
    } finally {
      setBusy(false);
    }
  }

  async function loginAsDemo() {
    setBusy(true);
    setError(null);
    try {
      await api.login("demo@example.com", "demopassword123");
      onDone();
    } catch (err: any) {
      setError(err?.message ?? "Could not sign in with demo credentials");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid items-start gap-10 py-2 lg:grid-cols-12 lg:gap-14 lg:py-8">
      <section className="animate-rise lg:col-span-7">
        <p className="label mb-5 flex items-center gap-2">
          <span aria-hidden="true" className="h-px w-6 bg-rule-strong" />
          Hair &amp; scalp, measured
        </p>
        <h1 className="text-5xl leading-[0.98] md:text-6xl">
          Your hair, <span className="marker">measured</span>
          <br />
          <span className="italic text-ink-soft">not guessed.</span>
        </h1>
        <p className="mt-6 max-w-[54ch] text-base leading-relaxed text-ink-soft">
          Photographs in, observations out. Every number states how sure it is, every claim cites its source, and
          anything worrying goes to a clinician instead of a shopping list.
        </p>
        <ol className="mt-10 max-w-xl divide-y divide-rule border-y border-rule">
          {PRINCIPLES.map((p, i) => (
            <li key={p.title} className="grid grid-cols-[3rem_1fr] gap-x-4 py-4">
              <span className="readout pt-1 text-sm text-ink-faint">{String(i + 1).padStart(2, "0")}</span>
              <div>
                <p className="font-display text-xl leading-tight">{p.title}</p>
                <p className="mt-1 text-sm leading-relaxed text-ink-soft">{p.body}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>

      <section className="animate-rise [animation-delay:120ms] lg:col-span-5">
        <div className="crop-marks">
          <div className="graph-paper border border-rule bg-surface p-6 sm:p-8">
            <p className="label">{mode === "login" ? "Sign in" : "New record"}</p>
            <h2 className="mt-2 text-3xl">{mode === "login" ? "Welcome back." : "Start your record."}</h2>
            <form onSubmit={submit} className="mt-6 space-y-4">
              <Field label="Email">
                <input
                  type="email"
                  required
                  autoComplete="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@example.com"
                  className={FIELD}
                />
              </Field>
              <Field label="Password" hint={mode === "register" ? "8 characters or more" : undefined}>
                <input
                  type="password"
                  required
                  minLength={8}
                  autoComplete={mode === "login" ? "current-password" : "new-password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className={FIELD}
                />
              </Field>
              {error && (
                <p role="alert" className="border-l-2 border-alert bg-alert-wash px-3 py-2 text-sm text-alert">
                  {error}
                </p>
              )}
              <Button type="submit" disabled={busy} size="lg" className="w-full">
                {busy ? "One moment…" : mode === "login" ? "Sign in" : "Create account"}
              </Button>
            </form>

            <div className="my-6 flex items-center gap-3" aria-hidden="true">
              <span className="h-px flex-1 bg-rule" />
              <span className="label">or</span>
              <span className="h-px flex-1 bg-rule" />
            </div>

            <Button type="button" variant="outline" size="lg" disabled={busy} onClick={loginAsDemo} className="w-full">
              Explore the demo record
            </Button>
            <p className="caption mt-2 text-center">3 scans · treatments · 30 days of adherence · no sign-up</p>

            <button
              onClick={() => {
                setError(null);
                setMode(mode === "login" ? "register" : "login");
              }}
              className="mt-6 w-full text-center text-sm text-ink-soft underline decoration-rule-strong underline-offset-4 hover:text-ink hover:decoration-ink"
            >
              {mode === "login" ? "New here? Create an account" : "Already have an account? Sign in"}
            </button>
          </div>
        </div>
        <p className="mt-4 flex items-start gap-2 px-2 text-xs leading-relaxed text-ink-faint">
          <ShieldCheck className="mt-px h-3.5 w-3.5 shrink-0" strokeWidth={1.75} />
          Photos are encrypted at rest, never sold, never used for facial recognition, and deletable at any time.
        </p>
      </section>
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
    <div className="mx-auto max-w-2xl animate-rise py-4">
      <p className="label mb-4 flex items-center gap-2">
        <span aria-hidden="true" className="h-px w-6 bg-rule-strong" />
        Consent · before analysis
      </p>
      <h1 className="text-4xl md:text-5xl">Before anything is analysed.</h1>
      <p className="mt-4 max-w-[60ch] font-display text-lg italic leading-snug text-ink-soft">
        Nothing is stored or measured until you agree. You can withdraw, export or permanently delete everything in
        Settings.
      </p>

      <fieldset className="mt-8 border-y border-rule">
        <legend className="sr-only">Consents</legend>
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
      </fieldset>

      <div className="mt-6 grid gap-4 sm:grid-cols-3">
        {GUARANTEES.map((g) => (
          <p key={g} className="border-t border-ink pt-2 text-sm leading-snug text-ink-soft">
            {g}
          </p>
        ))}
      </div>

      <Button onClick={save} disabled={!canProceed || busy} size="lg" className="mt-8 w-full sm:w-auto">
        <ShieldCheck className="h-4 w-4" strokeWidth={2} />
        {busy ? "Saving…" : "Agree and continue"}
      </Button>
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
    <label className="flex cursor-pointer items-center gap-4 border-b border-rule py-4 text-[0.95rem] last:border-b-0 hover:bg-surface-sunken/60">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="ml-1 h-[18px] w-[18px] shrink-0 accent-[hsl(var(--accent))]"
      />
      <span className="flex-1">{label}</span>
      <span className="label mr-1">{required ? "Required" : "Optional"}</span>
    </label>
  );
}
