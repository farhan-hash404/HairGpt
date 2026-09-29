"use client";

import * as React from "react";
import { AlertTriangle, Check, Plus, Stethoscope, X } from "lucide-react";
import { api, EMPTY_HISTORY, type ClinicalHistory } from "@/lib/api";
import { AuthGate } from "@/components/auth-gate";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/page-header";
import { cn } from "@/lib/utils";

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

const FIELD =
  "rounded border border-rule-strong bg-surface px-3.5 py-2.5 text-sm placeholder:text-ink-faint focus:border-ink focus:outline-none focus:ring-2 focus:ring-marker/70";

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
    <div className="mx-auto max-w-4xl animate-rise">
      <PageHeader
        index="Nº 06"
        eyebrow="Your history · self-reported"
        title={
          <>
            What photographs <span className="marker">can&apos;t</span> see.
          </>
        }
        dek="Thyroid problems, low iron and medication side effects are among the commonest, most treatable causes of hair loss, and none of them shows in a photo."
      />

      <Section letter="A" title="How it started">
        <ChoiceRow label="Did it start" options={ONSET} value={form.onset} onChange={(v) => set("onset", v)} />
        <ChoiceRow label="Where do you notice it" options={PATTERN} value={form.pattern} onChange={(v) => set("pattern", v)} />
        <NumberRow
          label="Roughly how many months has it been going on?"
          value={form.duration_months}
          onChange={(v) => set("duration_months", v)}
        />
      </Section>

      <Section letter="B" title="Family history">
        <CheckList>
          <CheckRow
            label="Hair loss runs in my family"
            checked={form.family_history_hair_loss}
            onChange={(v) => set("family_history_hair_loss", v)}
          />
        </CheckList>
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

      <Section letter="C" title="Health conditions" hint="Any of these can cause hair loss on their own, and are often treatable.">
        <CheckList>
          {CONDITIONS.map((c) => (
            <CheckRow key={c.key} label={c.label} checked={form[c.key] as boolean} onChange={(v) => set(c.key, v as never)} />
          ))}
        </CheckList>
      </Section>

      <Section letter="D" title="In the last year" hint="Shedding often begins two to four months after one of these.">
        <CheckList>
          {TRIGGERS.map((t) => (
            <CheckRow key={t.key} label={t.label} checked={form[t.key] as boolean} onChange={(v) => set(t.key, v as never)} />
          ))}
        </CheckList>
        {TRIGGERS.some((t) => form[t.key]) && (
          <NumberRow
            label="Roughly how many months ago?"
            value={form.trigger_months_ago}
            onChange={(v) => set("trigger_months_ago", v)}
          />
        )}
      </Section>

      <Section letter="E" title="Medications" hint="Anything you take regularly, prescription or not.">
        {form.medications.length > 0 && (
          <ul className="flex flex-wrap gap-2">
            {form.medications.map((m) => (
              <li key={m} className="inline-flex items-center gap-1.5 rounded-sm border border-ink bg-surface py-1 pl-2.5 pr-1 font-mono text-xs">
                {m}
                <button
                  onClick={() => set("medications", form.medications.filter((x) => x !== m))}
                  aria-label={`Remove ${m}`}
                  className="rounded-sm p-0.5 text-ink-faint hover:bg-surface-sunken hover:text-ink"
                >
                  <X className="h-3 w-3" />
                </button>
              </li>
            ))}
          </ul>
        )}
        <div className="flex max-w-md gap-2">
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
            className={cn(FIELD, "flex-1")}
          />
          <Button type="button" variant="outline" onClick={addMedication}>
            <Plus className="h-4 w-4" /> Add
          </Button>
        </div>

        {flagged.length > 0 && (
          <div className="border-l-2 border-caution bg-caution-wash px-4 py-3 text-sm">
            <p className="flex items-center gap-2 font-medium text-caution">
              <AlertTriangle className="h-4 w-4" />
              Worth raising with your prescriber
            </p>
            <p className="mt-1.5 leading-relaxed text-ink-soft">
              {flagged.join(", ")} {flagged.length === 1 ? "has" : "have"} a documented association with hair shedding.
              That does <strong className="text-ink">not</strong> mean it caused yours.{" "}
              <strong className="text-ink">Never stop a prescribed medication because of an app</strong>; bring it up
              with whoever prescribed it.
            </p>
          </div>
        )}
      </Section>

      <Section letter="F" title="Hair care">
        <CheckList>
          {STYLING.map((s) => (
            <CheckRow key={s.key} label={s.label} checked={form[s.key] as boolean} onChange={(v) => set(s.key, v as never)} />
          ))}
        </CheckList>
      </Section>

      <Section letter="G" title="Other symptoms">
        <CheckList>
          {SYMPTOMS.map((s) => (
            <CheckRow key={s.key} label={s.label} checked={form[s.key] as boolean} onChange={(v) => set(s.key, v as never)} />
          ))}
        </CheckList>
      </Section>

      <Section letter="H" title="Anything else">
        <textarea
          value={form.notes ?? ""}
          onChange={(e) => set("notes", e.target.value)}
          rows={3}
          placeholder="Anything you'd want a clinician to know."
          className={cn(FIELD, "w-full leading-relaxed")}
        />
      </Section>

      <div className="sticky bottom-20 z-10 mt-8 flex items-center gap-3 border-t border-ink bg-ground/90 py-4 backdrop-blur md:bottom-0">
        <Button onClick={save} disabled={busy} size="lg">
          {busy ? "Saving…" : "Save history"}
        </Button>
        {saved && (
          <span className="marker inline-flex items-center gap-1.5 text-sm font-medium text-[hsl(30_12%_10%)]" role="status">
            <Check className="h-4 w-4" strokeWidth={2.5} /> Saved
          </span>
        )}
      </div>

      <p className="caption mt-6 flex max-w-[80ch] gap-2.5">
        <Stethoscope className="mt-0.5 h-3.5 w-3.5 shrink-0" />
        Everything here is self-reported and recorded as such. HairGPT does not diagnose: this history decides when to
        suggest seeing a clinician, and goes into your doctor report so the conversation starts further along.
      </p>
    </div>
  );
}

/* An intake sheet: the question on the left, the answers ruled on the right. */
function Section({
  letter,
  title,
  hint,
  children,
}: {
  letter: string;
  title: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="grid gap-x-10 gap-y-4 border-t border-rule py-8 md:grid-cols-[15rem_1fr]">
      <div>
        <h2 className="flex items-baseline gap-2.5 text-xl">
          <span className="readout text-xs text-ink-faint">{letter}.</span>
          {title}
        </h2>
        {hint && <p className="mt-1.5 text-sm leading-relaxed text-ink-faint">{hint}</p>}
      </div>
      <div className="min-w-0 space-y-5">{children}</div>
    </section>
  );
}

function CheckList({ children }: { children: React.ReactNode }) {
  return <div className="border-t border-rule">{children}</div>;
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
    <label className="flex cursor-pointer items-center gap-3 border-b border-rule py-3 text-[0.95rem] transition-colors hover:bg-surface-sunken/60">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="ml-1 h-4 w-4 shrink-0 accent-[hsl(var(--ink))]"
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
      <p className="label mb-2">{label}</p>
      <div role="radiogroup" aria-label={label} className="inline-flex flex-wrap border border-rule-strong">
        {options.map((o, i) => {
          const active = value === o.value;
          return (
            <button
              key={o.value}
              type="button"
              role="radio"
              aria-checked={active}
              onClick={() => onChange(o.value)}
              className={cn(
                "px-3.5 py-2 text-sm transition-colors",
                i > 0 && "border-l border-rule-strong",
                active ? "bg-ink font-medium text-ground" : "bg-surface text-ink-soft hover:bg-surface-sunken hover:text-ink"
              )}
            >
              {o.label}
            </button>
          );
        })}
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
    <label className="block">
      <span className="label mb-2 block">{label}</span>
      <input
        type="number"
        min={0}
        value={value ?? ""}
        onChange={(e) => onChange(e.target.value === "" ? null : Number(e.target.value))}
        className={cn(FIELD, "readout w-32 text-base")}
      />
    </label>
  );
}
