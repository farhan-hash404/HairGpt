"use client";

import * as React from "react";
import { Check, Plus, Trash2 } from "lucide-react";
import { api } from "@/lib/api";
import { AuthGate } from "@/components/auth-gate";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { titleize } from "@/lib/utils";

const CATEGORIES = ["oral_med", "topical", "procedure", "shampoo", "scalp_care", "other"];

export default function TreatmentsPage() {
  return (
    <AuthGate>
      <Treatments />
    </AuthGate>
  );
}

function Treatments() {
  const [items, setItems] = React.useState<any[]>([]);
  const [summary, setSummary] = React.useState<any[]>([]);
  const [adding, setAdding] = React.useState(false);

  const load = React.useCallback(async () => {
    setItems(await api.listTreatments());
    setSummary(await api.adherenceSummary());
  }, []);

  React.useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Treatment tracker</h1>
          <p className="mt-1 max-w-xl text-sm text-muted-foreground">
            Record what you and your clinician have decided. HairGPT never prescribes medication — it only tracks what
            you enter and helps you prepare for clinical conversations.
          </p>
        </div>
        <Button onClick={() => setAdding((a) => !a)}>
          <Plus className="h-4 w-4" /> Add treatment
        </Button>
      </header>

      {adding && <AddForm onSaved={() => { setAdding(false); load(); }} />}

      <div className="space-y-3">
        {items.length === 0 && !adding && (
          <Card>
            <CardContent className="py-10 text-center text-muted-foreground">
              Nothing tracked yet. Add a medication, topical, shampoo, or procedure.
            </CardContent>
          </Card>
        )}
        {items.map((t) => {
          const a = summary.find((s) => s.treatment_id === t.id);
          return (
            <Card key={t.id}>
              <CardContent className="flex flex-wrap items-start justify-between gap-4 pt-5">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="font-medium">{t.name}</p>
                    <Badge variant="secondary">{titleize(t.category)}</Badge>
                    {t.is_prescribed_by_clinician && <Badge>clinician-prescribed</Badge>}
                  </div>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {[t.dose, t.frequency].filter(Boolean).join(" · ") || "No dose/frequency recorded"}
                  </p>
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    since {new Date(t.start_date).toLocaleDateString()}
                    {a ? ` · ${a.adherence_pct}% adherence (${a.window_days}d)` : ""}
                  </p>
                </div>
                <div className="flex gap-2">
                  <Button size="sm" variant="outline" onClick={async () => { await api.logAdherence(t.id, true); load(); }}>
                    <Check className="h-3.5 w-3.5" /> Took today
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    aria-label={`Delete ${t.name}`}
                    onClick={async () => { await api.deleteTreatment(t.id); load(); }}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      <Card className="bg-muted/40">
        <CardContent className="pt-5 text-xs text-muted-foreground">
          If a treatment is prescription-only, it must come from a qualified clinician. HairGPT will never tell you to
          start, stop, or change a prescription medication or its dose.
        </CardContent>
      </Card>
    </div>
  );
}

function AddForm({ onSaved }: { onSaved: () => void }) {
  const [form, setForm] = React.useState<any>({
    category: "topical",
    name: "",
    dose: "",
    frequency: "",
    is_prescribed_by_clinician: false,
  });
  const [busy, setBusy] = React.useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await api.createTreatment({ ...form, start_date: new Date().toISOString().slice(0, 10) });
      onSaved();
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Add a treatment</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={submit} className="grid gap-3 sm:grid-cols-2">
          <Field label="Name" required value={form.name} onChange={(v) => setForm({ ...form, name: v })} />
          <label className="text-sm">
            <span className="mb-1 block font-medium">Category</span>
            <select
              value={form.category}
              onChange={(e) => setForm({ ...form, category: e.target.value })}
              className="w-full rounded-xl border bg-background px-3 py-2 outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              {CATEGORIES.map((c) => (
                <option key={c} value={c}>
                  {titleize(c)}
                </option>
              ))}
            </select>
          </label>
          <Field label="Dose (as prescribed/label)" value={form.dose} onChange={(v) => setForm({ ...form, dose: v })} />
          <Field label="Frequency" value={form.frequency} onChange={(v) => setForm({ ...form, frequency: v })} />
          <label className="flex items-center gap-2 text-sm sm:col-span-2">
            <input
              type="checkbox"
              checked={form.is_prescribed_by_clinician}
              onChange={(e) => setForm({ ...form, is_prescribed_by_clinician: e.target.checked })}
              className="h-4 w-4 accent-[hsl(var(--primary))]"
            />
            This was prescribed by my clinician
          </label>
          <div className="sm:col-span-2">
            <Button type="submit" disabled={busy || !form.name}>
              {busy ? "Saving…" : "Save treatment"}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}

function Field({
  label,
  value,
  onChange,
  required,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  required?: boolean;
}) {
  return (
    <label className="text-sm">
      <span className="mb-1 block font-medium">{label}</span>
      <input
        required={required}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-xl border bg-background px-3 py-2 outline-none focus-visible:ring-2 focus-visible:ring-ring"
      />
    </label>
  );
}
