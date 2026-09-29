"use client";

import * as React from "react";
import { Download, LogOut, Trash2 } from "lucide-react";
import { api, clearTokens } from "@/lib/api";
import { AuthGate } from "@/components/auth-gate";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/page-header";
import { ReticleMark } from "@/components/wordmark";

const CONSENT_LABELS: Record<string, string> = {
  storage: "Store my photos securely (encrypted)",
  analysis: "Analyze my photos to produce observations",
  longitudinal: "Keep photos to compare over time",
  clinician_share: "Allow sharing a report with a clinician",
  research_optin: "Contribute de-identified data to research",
};

const GUARANTEES = [
  "Images are encrypted at rest and never sold or used for advertising.",
  "No facial recognition or identity matching is performed, ever.",
  "Access is audit-logged with hashed, minimal metadata; no raw IP addresses.",
];

export default function SettingsPage() {
  return (
    <AuthGate>
      <Settings />
    </AuthGate>
  );
}

function Settings() {
  const [me, setMe] = React.useState<any>(null);
  const [busy, setBusy] = React.useState(false);
  const [confirmText, setConfirmText] = React.useState("");

  const load = React.useCallback(async () => setMe(await api.me()), []);
  React.useEffect(() => {
    load();
  }, [load]);

  async function toggle(purpose: string, granted: boolean) {
    setBusy(true);
    await api.setConsent(purpose, granted);
    await load();
    setBusy(false);
  }

  async function exportData() {
    const res = await fetch("/api/v1/account/export", {
      method: "POST",
      headers: { Authorization: `Bearer ${localStorage.getItem("hairgpt.access")}` },
    });
    const blob = new Blob([JSON.stringify(await res.json(), null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "hairgpt-export.json";
    a.click();
    URL.revokeObjectURL(url);
  }

  async function deleteAccount() {
    if (confirmText !== "DELETE") return;
    await fetch("/api/v1/account", {
      method: "DELETE",
      headers: { Authorization: `Bearer ${localStorage.getItem("hairgpt.access")}` },
    });
    clearTokens();
    window.location.href = "/";
  }

  if (!me) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center gap-3 text-ink-soft">
        <ReticleMark className="h-6 w-6 animate-spin text-ink [animation-duration:2.4s]" />
        <p className="label">Loading settings…</p>
      </div>
    );
  }

  const consentMap: Record<string, boolean> = {};
  me.consents.forEach((c: any) => (consentMap[c.purpose] = c.granted));

  return (
    <div className="mx-auto max-w-3xl animate-rise">
      <PageHeader
        index="Nº 09"
        eyebrow="Settings & privacy"
        title={
          <>
            Your data, <span className="marker">your call</span>.
          </>
        }
        dek={<>Signed in as <span className="readout not-italic">{me.user.email}</span></>}
      />

      <section>
        <h2 className="mb-4 flex items-baseline gap-3 text-2xl">
          <span className="readout text-sm text-ink-faint">A.</span>
          Consent
        </h2>
        <div className="border-t border-ink">
          {Object.entries(CONSENT_LABELS).map(([purpose, label]) => {
            const required = purpose === "storage" || purpose === "analysis";
            return (
              <label
                key={purpose}
                className="flex cursor-pointer items-center gap-4 border-b border-rule py-4 text-[0.95rem] transition-colors hover:bg-surface-sunken/60"
              >
                <input
                  type="checkbox"
                  disabled={busy}
                  checked={!!consentMap[purpose]}
                  onChange={(e) => toggle(purpose, e.target.checked)}
                  className="ml-1 h-[18px] w-[18px] shrink-0 accent-[hsl(var(--ink))]"
                />
                <span className="flex-1">{label}</span>
                <span className="label mr-1">{required ? "Required for analysis" : "Optional"}</span>
              </label>
            );
          })}
        </div>
      </section>

      <section className="mt-14">
        <h2 className="mb-4 flex items-baseline gap-3 text-2xl">
          <span className="readout text-sm text-ink-faint">B.</span>
          Your data
        </h2>
        <div className="grid gap-4 sm:grid-cols-3">
          {GUARANTEES.map((g) => (
            <p key={g} className="border-t border-ink pt-2 text-sm leading-snug text-ink-soft">
              {g}
            </p>
          ))}
        </div>
        <div className="mt-6 flex flex-wrap gap-2">
          <Button variant="outline" onClick={exportData}>
            <Download className="h-4 w-4" /> Export my data
          </Button>
          <Button
            variant="ghost"
            onClick={() => {
              clearTokens();
              window.location.href = "/";
            }}
          >
            <LogOut className="h-4 w-4" /> Sign out
          </Button>
        </div>
      </section>

      <section className="mt-14 border-l-2 border-alert bg-alert-wash px-5 py-5 sm:px-6">
        <h2 className="flex items-baseline gap-3 text-2xl text-alert">
          <span className="readout text-sm">C.</span>
          Delete everything
        </h2>
        <p className="mt-2 max-w-[62ch] text-sm leading-relaxed text-ink-soft">
          Permanently deletes your account, scans, images, observations and treatments. This cannot be undone. Type{" "}
          <code className="readout rounded-sm border border-rule-strong bg-surface px-1">DELETE</code> to confirm.
        </p>
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <input
            value={confirmText}
            onChange={(e) => setConfirmText(e.target.value)}
            aria-label="Type DELETE to confirm"
            className="readout w-40 rounded border border-rule-strong bg-surface px-3.5 py-2.5 text-sm focus:border-alert focus:outline-none focus:ring-2 focus:ring-alert/30"
            placeholder="DELETE"
          />
          <Button variant="alert" disabled={confirmText !== "DELETE"} onClick={deleteAccount}>
            <Trash2 className="h-4 w-4" /> Permanently delete my account
          </Button>
        </div>
      </section>
    </div>
  );
}
