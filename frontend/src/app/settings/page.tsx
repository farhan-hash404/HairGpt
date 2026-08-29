"use client";

import * as React from "react";
import { Download, LogOut, ShieldCheck, Trash2 } from "lucide-react";
import { api, clearTokens } from "@/lib/api";
import { AuthGate } from "@/components/auth-gate";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const CONSENT_LABELS: Record<string, string> = {
  storage: "Store my photos securely (encrypted)",
  analysis: "Analyze my photos to produce observations",
  longitudinal: "Keep photos to compare over time",
  clinician_share: "Allow sharing a report with a clinician",
  research_optin: "Contribute de-identified data to research (optional)",
};

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

  if (!me) return <p className="text-muted-foreground">Loading…</p>;

  const consentMap: Record<string, boolean> = {};
  me.consents.forEach((c: any) => (consentMap[c.purpose] = c.granted));

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Settings &amp; privacy</h1>
        <p className="mt-1 text-sm text-muted-foreground">{me.user.email}</p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 text-primary" /> Consent
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {Object.entries(CONSENT_LABELS).map(([purpose, label]) => (
            <label key={purpose} className="flex items-center justify-between gap-3 rounded-xl border p-3 text-sm">
              <span>
                {label}
                {(purpose === "storage" || purpose === "analysis") && (
                  <Badge variant="outline" className="ml-2">required for analysis</Badge>
                )}
              </span>
              <input
                type="checkbox"
                disabled={busy}
                checked={!!consentMap[purpose]}
                onChange={(e) => toggle(purpose, e.target.checked)}
                className="h-4 w-4 accent-[hsl(var(--primary))]"
              />
            </label>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Your data</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <ul className="space-y-1 rounded-xl bg-muted/50 p-3 text-xs text-muted-foreground">
            <li>• Images are encrypted at rest and never sold or used for advertising.</li>
            <li>• No facial recognition or identity matching is performed, ever.</li>
            <li>• Access is audit-logged with hashed, minimal metadata (no raw IP addresses).</li>
          </ul>
          <div className="flex flex-wrap gap-3">
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
        </CardContent>
      </Card>

      <Card className="border-destructive/40">
        <CardHeader>
          <CardTitle className="text-destructive">Delete everything</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm text-muted-foreground">
            Permanently deletes your account, scans, images, observations, and treatments. This cannot be undone. Type{" "}
            <code className="rounded bg-muted px-1">DELETE</code> to confirm.
          </p>
          <input
            value={confirmText}
            onChange={(e) => setConfirmText(e.target.value)}
            className="w-40 rounded-xl border bg-background px-3 py-2 text-sm"
            placeholder="DELETE"
          />
          <div>
            <Button variant="destructive" disabled={confirmText !== "DELETE"} onClick={deleteAccount}>
              <Trash2 className="h-4 w-4" /> Permanently delete my account
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
