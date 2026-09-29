"use client";

import * as React from "react";
import { Check, Plus, Trash2, X } from "lucide-react";
import { api } from "@/lib/api";
import { AuthGate } from "@/components/auth-gate";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/page-header";
import { Readout } from "@/components/readout";
import { cn, titleize } from "@/lib/utils";

const CATEGORIES = ["oral_med", "topical", "procedure", "shampoo", "scalp_care", "other"];

const FIELD =
  "w-full rounded border border-rule-strong bg-surface px-3.5 py-2.5 text-sm placeholder:text-ink-faint focus:border-ink focus:outline-none focus:ring-2 focus:ring-marker/70";

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
    <div className="mx-auto max-w-4xl animate-rise">
      <PageHeader
        index="Nº 07"
        eyebrow="Treatments & regimen"
        title={
          <>
            What you&apos;ve decided, <span className="marker">tracked</span>.
          </>
        }
        dek="Record what you and your clinician have agreed. HairGPT never prescribes; it keeps the log and helps you prepare for the conversation."
        actions={
          <Button onClick={() => setAdding((a) => !a)} variant={adding ? "outline" : "default"}>
            {adding ? <X className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
            {adding ? "Close" : "Add treatment"}
          </Button>
        }
      />

      {adding && (
        <AddForm
          onSaved={() => {
            setAdding(false);
            load();
          }}
        />
      )}

      {items.length === 0 && !adding ? (
        <p className="border-y border-rule py-8 text-center text-sm text-ink-soft">
          Nothing tracked yet. Add a medication, topical, shampoo or procedure.
        </p>
      ) : (
        <ul className="border-t border-ink">
          {items.map((t, i) => {
            const a = summary.find((s) => s.treatment_id === t.id);
            return (
              <li key={t.id} className="grid gap-x-6 gap-y-3 border-b border-rule py-5 md:grid-cols-[2.5rem_1fr_8rem_auto] md:items-center">
                <span className="readout hidden text-xs text-ink-faint md:block">{String(i + 1).padStart(2, "0")}</span>
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="font-display text-xl leading-tight">{t.name}</p>
                    <Badge variant="neutral">{titleize(t.category)}</Badge>
                    {t.is_prescribed_by_clinician && <Badge variant="default">clinician-prescribed</Badge>}
                  </div>
                  <p className="mt-1 text-sm text-ink-soft">
                    {[t.dose, t.frequency].filter(Boolean).join(" · ") || "No dose or frequency recorded"}
                  </p>
                  <p className="caption mt-0.5">
                    since {new Date(t.start_date).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" })}
                  </p>
                </div>
                <div className="md:text-right">
                  {a ? (
                    <>
                      <Readout value={a.adherence_pct} suffix="%" className="text-2xl font-medium tracking-[-0.03em]" />
                      <p className="caption">adherence, {a.window_days} days</p>
                    </>
                  ) : (
                    <p className="caption">no logs yet</p>
                  )}
                </div>
                <div className="flex gap-1.5">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={async () => {
                      await api.logAdherence(t.id, true);
                      load();
                    }}
                  >
                    <Check className="h-3.5 w-3.5" /> Took today
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    aria-label={`Delete ${t.name}`}
                    onClick={async () => {
                      await api.deleteTreatment(t.id);
                      load();
                    }}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </li>
            );
          })}
        </ul>
      )}

      <p className="caption mt-8 max-w-[80ch] border-l-2 border-ink pl-3">
        If a treatment is prescription-only, it must come from a qualified clinician. HairGPT will never tell you to
        start, stop, or change a prescription medication or its dose.
      </p>
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
    <div className="crop-marks mb-10 animate-rise">
      <form onSubmit={submit} className="grid gap-4 border border-rule bg-surface p-5 sm:grid-cols-2 sm:p-7">
        <p className="label sm:col-span-2">New entry</p>
        <Field label="Name" required value={form.name} onChange={(v) => setForm({ ...form, name: v })} />
        <label className="block">
          <span className="label mb-1.5 block">Category</span>
          <select
            value={form.category}
            onChange={(e) => setForm({ ...form, category: e.target.value })}
            className={FIELD}
          >
            {CATEGORIES.map((c) => (
              <option key={c} value={c}>
                {titleize(c)}
              </option>
            ))}
          </select>
        </label>
        <Field label="Dose (as prescribed or on the label)" value={form.dose} onChange={(v) => setForm({ ...form, dose: v })} />
        <Field label="Frequency" value={form.frequency} onChange={(v) => setForm({ ...form, frequency: v })} />
        <label className="flex items-center gap-2.5 text-sm sm:col-span-2">
          <input
            type="checkbox"
            checked={form.is_prescribed_by_clinician}
            onChange={(e) => setForm({ ...form, is_prescribed_by_clinician: e.target.checked })}
            className="h-4 w-4 accent-[hsl(var(--ink))]"
          />
          This was prescribed by my clinician
        </label>
        <div className="border-t border-rule pt-4 sm:col-span-2">
          <Button type="submit" disabled={busy || !form.name}>
            {busy ? "Saving…" : "Save treatment"}
          </Button>
        </div>
      </form>
    </div>
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
    <label className="block">
      <span className="label mb-1.5 block">{label}</span>
      <input required={required} value={value} onChange={(e) => onChange(e.target.value)} className={cn(FIELD)} />
    </label>
  );
}
