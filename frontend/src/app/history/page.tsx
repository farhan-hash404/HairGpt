"use client";

import * as React from "react";
import { AlertTriangle, Check, Plus, Stethoscope, X } from "lucide-react";
import { api, EMPTY_HISTORY, type ClinicalHistory } from "@/lib/api";
import { AuthGate } from "@/components/auth-gate";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function HistoryPage() {
  return (
    <AuthGate>
      <History />
    </AuthGate>
  );
}

const ONSET = [
  { value: "gradual", label: "Gradually" },
  { value: "sudden", label: "Suddenly" },
  { value: "unsure", label: "Not sure" },
];

const PATTERN = [
  { value: "receding", label: "Receding hairline" },
  { value: "crown", label: "Thinning at the crown" },
  { value: "diffuse", label: "All over" },
  { value: "patchy", label: "In patches" },
  { value: "unsure", label: "Not sure" },
];

const CONDITIONS: { key: keyof ClinicalHistory; label: string }[] = [
  { key: "thyroid_condition", label: "Thyroid condition" },
  { key: "iron_deficiency", label: "Iron deficiency or anaemia" },
  { key: "autoimmune_condition", label: "An autoimmune condition" },
  { key: "pcos", label: "PCOS" },
  { key: "scalp_condition", label: "A diagnosed scalp condition" },
];

const TRIGGERS: { key: keyof ClinicalHistory; label: string }[] = [
  { key: "recent_illness", label: "A significant illness" },
  { key: "recent_surgery", label: "Surgery" },
  { key: "major_stress", label: "A period of major stress" },
  { key: "rapid_weight_loss", label: "Rapid weight loss" },
  { key: "postpartum", label: "Childbirth" },
];

const STYLING: { key: keyof ClinicalHistory; label: string }[] = [
  { key: "tight_hairstyles", label: "Tight braids, weaves, or ponytails" },
  { key: "chemical_treatments", label: "Relaxers, bleach, or perms" },
  { key: "heat_styling", label: "Frequent heat styling" },
];

const SYMPTOMS: { key: keyof ClinicalHistory; label: string }[] = [
  { key: "scalp_itch", label: "Itchy scalp" },
  { key: "scalp_pain", label: "Painful or tender scalp" },
  { key: "body_hair_change", label: "Change in body or facial hair" },
  { key: "menstrual_irregularity", label: "Irregular periods" },
];

function History() {
  const [form, setForm] = React.useState<ClinicalHistory>(EMPTY_HISTORY);
  const [medInput, setMedInput] = React.useState("");
  const [saved, setSaved] = React.useState(false);
  const [busy, setBusy] = React.useState(false);
  const [flagged, setFlagged] = React.useState<string[]>([]);

  React.useEffect(() => {
    api.getHistory().then((h) => {
      if (h) {
        setForm({ ...EMPTY_HISTORY, ...h });
        setFlagged(h.flagged_medications ?? []);
      }
    });
  }, []);

  function set<K extends keyof ClinicalHistory>(key: K, value: ClinicalHistory[K]) {
    setForm((f) => ({ ...f, [key]: value }));
    setSaved(false);
  }

  async function save() {
    setBusy(true);
    try {
      const result = await api.saveHistory(form);
      setFlagged(result.flagged_medications ?? []);
      setSaved(true);
    } finally {
      setBusy(false);
    }
  }

  function addMedication() {
    const name = medInput.trim();
    if (!name || form.medications.includes(name)) return;
    set("medications", [...form.medications, name]);
    setMedInput("");
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Your history</h1>
        <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
          Photos can&apos;t show thyroid problems, low iron, or a medication side effect — yet these are among the most
          common and most treatable causes of hair loss. A few minutes here makes everything else more useful.
        </p>
      </header>

      <Section title="How it started">
        <ChoiceRow
          label="Did it start"
          options={ONSET}
          value={form.onset}
          onChange={(v) => set("onset", v)}
        />
        <ChoiceRow
          label="Where do you notice it"
          options={PATTERN}
          value={form.pattern}
          onChange={(v) => set("pattern", v)}
        />
        <NumberRow
          label="Roughly how many months has it been going on?"
          value={form.duration_months}
          onChange={(v) => set("duration_months", v)}
        />
      </Section>

      <Section title="Family history">
        <CheckRow
          label="Hair loss runs in my family"
          checked={form.family_history_hair_loss}
          onChange={(v) => set("family_history_hair_loss", v)}
        />
        {form.family_history_hair_loss && (
          <ChoiceRow
            label="Which side"
            options={[
              { value: "maternal", label: "Mother's side" },
              { value: "paternal", label: "Father's side" },
              { value: "both", label: "Both" },
              { value: "unsure", label: "Not sure" },
            ]}
            value={form.family_history_side}
            onChange={(v) => set("family_history_side", v)}
          />
        )}
      </Section>

      <Section
        title="Health conditions"
        hint="Any of these can cause hair loss on their own, and are often treatable."
      >
        {CONDITIONS.map((c) => (
          <CheckRow
            key={c.key}
            label={c.label}
            checked={form[c.key] as boolean}
            onChange={(v) => set(c.key, v as never)}
          />
        ))}
      </Section>

      <Section
        title="In the last year"
        hint="Shedding often begins two to four months after one of these."
      >
        {TRIGGERS.map((t) => (
          <CheckRow
            key={t.key}
            label={t.label}
            checked={form[t.key] as boolean}
            onChange={(v) => set(t.key, v as never)}
          />
        ))}
        {TRIGGERS.some((t) => form[t.key]) && (
          <NumberRow
            label="Roughly how many months ago?"
            value={form.trigger_months_ago}
            onChange={(v) => set("trigger_months_ago", v)}
          />
        )}
      </Section>

      <Section title="Medications" hint="Include anything you take regularly, prescription or not.">
        <div className="flex flex-wrap gap-2">
          {form.medications.map((m) => (
            <span
              key={m}
              className="inline-flex items-center gap-1.5 rounded-full border bg-muted/50 px-3 py-1 text-sm"
            >
              {m}
              <button
                onClick={() => set("medications", form.medications.filter((x) => x !== m))}
                aria-label={`Remove ${m}`}
                className="text-muted-foreground hover:text-foreground"
              >
                <X className="h-3 w-3" />
              </button>
            </span>
          ))}
        </div>
        <div className="flex gap-2">
          <input
            value={medInput}
            onChange={(e) => setMedInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                addMedication();
              }
            }}
            placeholder="e.g. levothyroxine"
            className="flex-1 rounded-xl border bg-background px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />
          <Button type="button" variant="outline" onClick={addMedication}>
            <Plus className="h-4 w-4" /> Add
          </Button>
        </div>

        {flagged.length > 0 && (
          <div className="rounded-xl border border-[hsl(var(--caution))]/40 bg-[hsl(var(--caution))]/10 p-3 text-sm">
            <p className="flex items-center gap-2 font-medium">
              <AlertTriangle className="h-4 w-4 text-[hsl(var(--caution))]" />
              Worth raising with your prescriber
            </p>
            <p className="mt-1 text-muted-foreground">
              {flagged.join(", ")} {flagged.length === 1 ? "has" : "have"} a documented association with hair shedding.
              That does <strong>not</strong> mean it caused yours.{" "}
              <strong>Never stop a prescribed medication because of an app</strong> — bring it up with whoever prescribed it.
            </p>
          </div>
        )}
      </Section>

      <Section title="Hair care">
        {STYLING.map((s) => (
          <CheckRow
            key={s.key}
            label={s.label}
            checked={form[s.key] as boolean}
            onChange={(v) => set(s.key, v as never)}
          />
        ))}
      </Section>

      <Section title="Other symptoms">
        {SYMPTOMS.map((s) => (
          <CheckRow
            key={s.key}
            label={s.label}
            checked={form[s.key] as boolean}
            onChange={(v) => set(s.key, v as never)}
          />
        ))}
      </Section>

      <Section title="Anything else">
        <textarea
          value={form.notes ?? ""}
          onChange={(e) => set("notes", e.target.value)}
          rows={3}
          placeholder="Anything you'd want a clinician to know."
          className="w-full rounded-xl border bg-background px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
        />
      </Section>

      <div className="flex items-center gap-3">
        <Button onClick={save} disabled={busy} size="lg">
          {busy ? "Saving…" : "Save history"}
        </Button>
        {saved && (
          <span className="flex items-center gap-1.5 text-sm text-primary">
            <Check className="h-4 w-4" /> Saved
          </span>
        )}
      </div>

      <Card className="bg-muted/40">
        <CardContent className="flex gap-3 pt-5 text-xs text-muted-foreground">
          <Stethoscope className="mt-0.5 h-4 w-4 shrink-0" />
          <p>
            Everything here is self-reported and recorded as such. HairGPT does not diagnose — this history is used to
            decide when to recommend seeing a clinician, and is included in your doctor report so the conversation
            starts further along.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

function Section({ title, hint, children }: { title: string; hint?: string; children: React.ReactNode }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{title}</CardTitle>
        {hint && <p className="text-sm text-muted-foreground">{hint}</p>}
      </CardHeader>
      <CardContent className="space-y-3">{children}</CardContent>
    </Card>
  );
}

function CheckRow({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <label className="flex cursor-pointer items-center gap-3 rounded-xl border p-3 text-sm hover:bg-muted/40">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="h-4 w-4 accent-[hsl(var(--primary))]"
      />
      {label}
    </label>
  );
}

function ChoiceRow({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: { value: string; label: string }[];
  value: string | null;
  onChange: (v: string) => void;
}) {
  return (
    <div>
      <p className="mb-2 text-sm font-medium">{label}</p>
      <div className="flex flex-wrap gap-2">
        {options.map((o) => (
          <button
            key={o.value}
            type="button"
            onClick={() => onChange(o.value)}
            className={`rounded-full border px-3 py-1.5 text-sm transition-colors ${
              value === o.value
                ? "border-primary bg-primary/10 text-primary"
                : "text-muted-foreground hover:bg-muted"
            }`}
          >
            {o.label}
          </button>
        ))}
      </div>
    </div>
  );
}

function NumberRow({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number | null;
  onChange: (v: number | null) => void;
}) {
  return (
    <label className="block text-sm">
      <span className="mb-1 block font-medium">{label}</span>
      <input
        type="number"
        min={0}
        value={value ?? ""}
        onChange={(e) => onChange(e.target.value === "" ? null : Number(e.target.value))}
        className="w-32 rounded-xl border bg-background px-3 py-2 outline-none focus-visible:ring-2 focus-visible:ring-ring"
      />
    </label>
  );
}
