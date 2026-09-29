"use client";

import * as React from "react";
import { Check, Sparkles, User, HelpCircle, Shield, Camera, HeartPulse, Stethoscope, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

export type StepId = "profile" | "story" | "health" | "safety" | "capture" | "reading";

export const STEPS: { id: StepId; label: string; blurb: string; icon: any }[] = [
  { id: "profile", label: "About You", blurb: "Calibrates model accuracy for your group", icon: User },
  { id: "story", label: "Hair Story", blurb: "Onset timeline, patterns & family history", icon: HeartPulse },
  { id: "health", label: "Health & Routine", blurb: "Medical factors, stress & hair habits", icon: Stethoscope },
  { id: "safety", label: "Safety Check", blurb: "Identifies signs requiring a clinician", icon: Shield },
  { id: "capture", label: "Photo Capture", blurb: "Guided multi-view scan with live feedback", icon: Camera },
];

/** Modern responsive progress stepper */
export function StepRail({
  current,
  furthest,
  onJump,
}: {
  current: StepId;
  furthest: number;
  onJump: (id: StepId, index: number) => void;
}) {
  const currentIndex = Math.max(0, STEPS.findIndex((s) => s.id === current));
  const progressPct = Math.round(((currentIndex + 1) / STEPS.length) * 100);

  return (
    <nav aria-label="Assessment progress" className="mb-6 lg:mb-0">
      {/* Mobile top progress card */}
      <div className="rounded-2xl border border-rule bg-surface p-4 shadow-xs lg:hidden">
        <div className="flex items-center justify-between gap-2 mb-2">
          <div className="flex items-center gap-2">
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-accent text-[11px] font-bold text-white">
              {currentIndex + 1}
            </span>
            <span className="text-sm font-semibold text-ink">
              {STEPS[currentIndex]?.label}
            </span>
          </div>
          <span className="text-xs font-semibold text-accent">
            {progressPct}% Done
          </span>
        </div>
        <div className="h-2 w-full overflow-hidden rounded-full bg-rule">
          <div
            className="h-full rounded-full bg-gradient-to-r from-accent to-blue-400 transition-all duration-300 ease-out"
            style={{ width: `${progressPct}%` }}
          />
        </div>
      </div>

      {/* Desktop vertical sidebar rail */}
      <div className="hidden rounded-2xl border border-rule bg-surface p-4 shadow-xs lg:block">
        <div className="mb-4 px-2">
          <p className="text-xs font-bold uppercase tracking-wider text-ink-faint">Assessment Steps</p>
          <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-rule">
            <div
              className="h-full rounded-full bg-accent transition-all duration-300 ease-out"
              style={{ width: `${progressPct}%` }}
            />
          </div>
        </div>

        <ol className="space-y-1">
          {STEPS.map((step, i) => {
            const done = i < currentIndex;
            const active = i === currentIndex;
            const reachable = i <= furthest;
            const Icon = step.icon;

            return (
              <li key={step.id}>
                <button
                  type="button"
                  onClick={() => reachable && onJump(step.id, i)}
                  disabled={!reachable}
                  aria-current={active ? "step" : undefined}
                  className={cn(
                    "flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left transition-all",
                    active
                      ? "bg-accent-wash text-accent font-semibold shadow-xs"
                      : done
                        ? "text-ink hover:bg-surface-sunken"
                        : "text-ink-faint opacity-55",
                    !reachable && "cursor-not-allowed"
                  )}
                >
                  <div
                    className={cn(
                      "flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-xs font-medium transition-colors",
                      active
                        ? "bg-accent text-white shadow-sm"
                        : done
                          ? "bg-ok-wash text-ok font-bold"
                          : "bg-surface-sunken text-ink-faint"
                    )}
                  >
                    {done ? <Check className="h-4 w-4" /> : <Icon className="h-4 w-4" />}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className={cn("truncate text-sm", active ? "text-accent font-semibold" : "text-ink")}>
                      {step.label}
                    </p>
                    <p className="truncate text-xs text-ink-faint">{step.blurb}</p>
                  </div>
                </button>
              </li>
            );
          })}
        </ol>
      </div>
    </nav>
  );
}

/** Consistent clean card frame for assessment steps */
export function StepPanel({
  title,
  intro,
  badge,
  children,
}: {
  title: string;
  intro?: string;
  badge?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-2xl border border-rule bg-surface p-6 sm:p-8 shadow-xs animate-rise">
      <div className="mb-6 border-b border-rule pb-5">
        {badge && (
          <span className="mb-2 inline-flex items-center gap-1 rounded-full bg-accent-wash px-2.5 py-0.5 text-xs font-semibold text-accent">
            <Sparkles className="h-3 w-3" />
            {badge}
          </span>
        )}
        <h1 className="text-2xl font-bold tracking-tight text-ink sm:text-3xl">{title}</h1>
        {intro && <p className="mt-2 text-sm leading-relaxed text-ink-soft max-w-2xl">{intro}</p>}
      </div>
      <div className="space-y-8">{children}</div>
    </div>
  );
}

export function Fieldset({
  legend,
  hint,
  children,
}: {
  legend: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-3">
      <div>
        <h3 className="text-base font-semibold text-ink">{legend}</h3>
        {hint && <p className="mt-0.5 text-xs text-ink-faint leading-relaxed">{hint}</p>}
      </div>
      <div>{children}</div>
    </div>
  );
}

/** Visual Fitzpatrick Skin Tone Picker with realistic gradient swatches */
export const SKIN_TONES = [
  {
    type: 1,
    name: "Type I",
    desc: "Very fair, ivory. Always burns, freckles easily.",
    colors: "from-[#ffeedf] to-[#fce4d6]",
    border: "#f0d5c2",
  },
  {
    type: 2,
    name: "Type II",
    desc: "Fair, peach. Usually burns, tans with difficulty.",
    colors: "from-[#f5d5be] to-[#eccbb4]",
    border: "#deba9f",
  },
  {
    type: 3,
    name: "Type III",
    desc: "Medium, golden. Mild burn risk, tans gradually.",
    colors: "from-[#e2b79a] to-[#d4a889]",
    border: "#c59877",
  },
  {
    type: 4,
    name: "Type IV",
    desc: "Olive, light brown. Rarely burns, tans easily.",
    colors: "from-[#c6906e] to-[#b77f5c]",
    border: "#a86e49",
  },
  {
    type: 5,
    name: "Type V",
    desc: "Brown, rich bronze. Very rarely burns, tans deeply.",
    colors: "from-[#9a6442] to-[#885433]",
    border: "#774526",
  },
  {
    type: 6,
    name: "Type VI",
    desc: "Deep brown / ebony. Never burns, deeply pigmented.",
    colors: "from-[#5d3b2a] to-[#4c2d1d]",
    border: "#3d2214",
  },
];

export function SkinTonePicker({
  value,
  onChange,
}: {
  value: number | null;
  onChange: (type: number | null) => void;
}) {
  return (
    <div className="space-y-3">
      <div className="grid gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
        {SKIN_TONES.map((tone) => {
          const selected = value === tone.type;
          return (
            <button
              key={tone.type}
              type="button"
              onClick={() => onChange(tone.type)}
              className={cn(
                "group relative flex items-start gap-3.5 rounded-xl border p-3.5 text-left transition-all",
                selected
                  ? "border-accent bg-accent-wash/60 ring-2 ring-accent/30 shadow-xs"
                  : "border-rule bg-surface hover:border-accent-edge hover:bg-surface-sunken"
              )}
            >
              {/* Color swatch circle */}
              <div
                className={cn(
                  "h-10 w-10 shrink-0 rounded-full bg-gradient-to-br shadow-inner ring-2",
                  tone.colors
                )}
                style={{ borderColor: tone.border }}
              />

              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between gap-1">
                  <span className="text-sm font-semibold text-ink">{tone.name}</span>
                  {selected && <Check className="h-4 w-4 text-accent" />}
                </div>
                <p className="mt-0.5 text-xs text-ink-soft leading-snug">{tone.desc}</p>
              </div>
            </button>
          );
        })}
      </div>

      <button
        type="button"
        onClick={() => onChange(null)}
        className={cn(
          "inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors",
          value === null ? "bg-surface-sunken text-ink font-semibold" : "text-ink-faint hover:text-ink"
        )}
      >
        <HelpCircle className="h-3.5 w-3.5" />
        <span>I'd prefer not to answer</span>
      </button>
    </div>
  );
}

/** Visual Hair Loss Pattern Selector with rich cards */
export const PATTERNS = [
  {
    id: "receding",
    title: "Receding Hairline",
    subtitle: "Thinning primarily at the temples or forehead line",
    badge: "Frontal",
  },
  {
    id: "crown",
    title: "Crown / Vertex",
    subtitle: "Thinning or bald spot at the top-back swirl area",
    badge: "Top Swirl",
  },
  {
    id: "diffuse",
    title: "Overall Diffuse",
    subtitle: "Even thinning across the entire scalp with lower density",
    badge: "All Over",
  },
  {
    id: "patchy",
    title: "Patchy Loss",
    subtitle: "Distinct round or oval bare spots appearing suddenly",
    badge: "Focal",
  },
  {
    id: "unsure",
    title: "General Prevention / Unsure",
    subtitle: "Baseline routine tracking or unsure where thinning is focused",
    badge: "Routine",
  },
];

export function PatternPicker({
  value,
  onChange,
}: {
  value: string | null;
  onChange: (id: string) => void;
}) {
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {PATTERNS.map((p) => {
        const selected = value === p.id;
        return (
          <button
            key={p.id}
            type="button"
            onClick={() => onChange(p.id)}
            className={cn(
              "group relative flex flex-col justify-between rounded-xl border p-4 text-left transition-all",
              selected
                ? "border-accent bg-accent-wash/70 ring-2 ring-accent/30 shadow-xs"
                : "border-rule bg-surface hover:border-accent-edge hover:bg-surface-sunken"
            )}
          >
            <div>
              <div className="flex items-center justify-between gap-2">
                <span className="text-sm font-semibold text-ink">{p.title}</span>
                <span
                  className={cn(
                    "rounded-full px-2 py-0.5 text-[11px] font-medium",
                    selected ? "bg-accent text-white" : "bg-surface-sunken text-ink-faint"
                  )}
                >
                  {p.badge}
                </span>
              </div>
              <p className="mt-1.5 text-xs text-ink-soft leading-relaxed">{p.subtitle}</p>
            </div>
            {selected && (
              <div className="mt-3 flex items-center gap-1 text-xs font-semibold text-accent">
                <Check className="h-3.5 w-3.5" />
                <span>Selected</span>
              </div>
            )}
          </button>
        );
      })}
    </div>
  );
}

/** Interactive card selection group */
export function ChoiceCardGroup({
  value,
  options,
  onChange,
}: {
  value: string | null;
  options: { value: string; label: string; description?: string }[];
  onChange: (v: string) => void;
}) {
  return (
    <div className="grid gap-2.5 sm:grid-cols-2 md:grid-cols-3">
      {options.map((o) => {
        const selected = value === o.value;
        return (
          <button
            key={o.value}
            type="button"
            onClick={() => onChange(o.value)}
            className={cn(
              "flex items-center justify-between rounded-xl border p-3.5 text-left transition-all",
              selected
                ? "border-accent bg-accent-wash text-accent font-semibold ring-2 ring-accent/20"
                : "border-rule bg-surface text-ink-soft hover:border-accent-edge hover:bg-surface-sunken hover:text-ink"
            )}
          >
            <div>
              <span className="text-sm font-medium">{o.label}</span>
              {o.description && <p className="text-xs text-ink-faint mt-0.5">{o.description}</p>}
            </div>
            {selected && <Check className="h-4 w-4 shrink-0 text-accent" />}
          </button>
        );
      })}
    </div>
  );
}

/** Interactive tag chip for multi-select checklists */
export function TagChip({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <button
      type="button"
      onClick={() => onChange(!checked)}
      className={cn(
        "inline-flex items-center gap-2 rounded-xl border px-3.5 py-2.5 text-sm font-medium transition-all",
        checked
          ? "border-accent bg-accent text-white shadow-xs"
          : "border-rule bg-surface text-ink hover:border-rule-strong hover:bg-surface-sunken"
      )}
    >
      <div
        className={cn(
          "flex h-4 w-4 items-center justify-center rounded border transition-colors",
          checked ? "border-white bg-white text-accent" : "border-ink-faint bg-transparent"
        )}
      >
        {checked && <Check className="h-3 w-3 stroke-[3]" />}
      </div>
      <span>{label}</span>
    </button>
  );
}

/** Medication tag cloud with quick-add chips */
export function MedicationInput({
  medications,
  onChange,
}: {
  medications: string[];
  onChange: (meds: string[]) => void;
}) {
  const [input, setInput] = React.useState("");

  const POPULAR_MEDS = ["Minoxidil", "Finasteride", "Biotin", "Iron Supplement", "Multivitamin", "Levothyroxine"];

  const addMed = (name: string) => {
    const trimmed = name.trim();
    if (trimmed && !medications.some((m) => m.toLowerCase() === trimmed.toLowerCase())) {
      onChange([...medications, trimmed]);
      setInput("");
    }
  };

  const removeMed = (name: string) => {
    onChange(medications.filter((m) => m !== name));
  };

  return (
    <div className="space-y-3">
      {/* Current tags */}
      {medications.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {medications.map((m) => (
            <span
              key={m}
              className="inline-flex items-center gap-1.5 rounded-lg bg-accent-wash border border-accent-edge px-3 py-1.5 text-xs font-semibold text-accent"
            >
              {m}
              <button
                type="button"
                onClick={() => removeMed(m)}
                className="hover:opacity-75 text-accent font-bold"
                aria-label={`Remove ${m}`}
              >
                ×
              </button>
            </span>
          ))}
        </div>
      )}

      {/* Input row */}
      <div className="flex gap-2 max-w-md">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              addMed(input);
            }
          }}
          placeholder="Type a medication & press enter..."
          className="flex-1 rounded-xl border border-rule bg-surface px-3.5 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent"
        />
        <button
          type="button"
          onClick={() => addMed(input)}
          className="rounded-xl bg-surface-sunken border border-rule px-4 py-2 text-sm font-medium hover:bg-surface hover:border-accent-edge"
        >
          Add
        </button>
      </div>

      {/* Quick suggest pills */}
      <div>
        <p className="text-xs text-ink-faint mb-1.5">Commonly reported:</p>
        <div className="flex flex-wrap gap-1.5">
          {POPULAR_MEDS.filter((p) => !medications.includes(p)).map((item) => (
            <button
              key={item}
              type="button"
              onClick={() => addMed(item)}
              className="rounded-full border border-rule bg-surface px-2.5 py-1 text-xs text-ink-soft hover:border-accent hover:text-accent transition-colors"
            >
              + {item}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
