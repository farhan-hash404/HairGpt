"use client";

import * as React from "react";
import { Check, HelpCircle, Plus, X } from "lucide-react";
import { cn } from "@/lib/utils";

export type StepId = "profile" | "story" | "health" | "safety" | "capture" | "reading";

export const STEPS: { id: StepId; label: string; blurb: string }[] = [
  { id: "profile", label: "About you", blurb: "Calibrates the readings for your group" },
  { id: "story", label: "Hair story", blurb: "Onset, pattern and family history" },
  { id: "health", label: "Health & routine", blurb: "Medical factors, stress and styling" },
  { id: "safety", label: "Safety check", blurb: "Signs that need a clinician first" },
  { id: "capture", label: "Photo capture", blurb: "Guided views with live quality checks" },
];

/* Selected choices: ink edge plus a highlighter stroke, never a coloured fill. */
const SELECTED = "border-ink bg-surface text-ink shadow-[inset_3px_0_0_hsl(var(--marker))]";
const UNSELECTED = "border-rule bg-surface text-ink-soft hover:border-rule-strong hover:bg-surface-sunken hover:text-ink";

/** The assessment's table of contents. */
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

  const segments = (
    <div className="flex gap-1" aria-hidden="true">
      {STEPS.map((s, i) => (
        <span
          key={s.id}
          className={cn("h-[3px] flex-1 transition-colors duration-300", i <= currentIndex ? "bg-ink" : "bg-rule")}
        />
      ))}
    </div>
  );

  return (
    <nav aria-label="Assessment progress" className="mb-8 lg:mb-0">
      <div className="lg:hidden">
        <p className="label mb-2 flex items-center justify-between">
          <span>
            Step {currentIndex + 1} of {STEPS.length}
          </span>
          <span className="text-ink">{STEPS[currentIndex]?.label}</span>
        </p>
        {segments}
      </div>

      <div className="hidden lg:block">
        <p className="label mb-3">Assessment</p>
        {segments}
        <ol className="mt-5 border-t border-rule">
          {STEPS.map((step, i) => {
            const done = i < currentIndex;
            const active = i === currentIndex;
            const reachable = i <= furthest;
            return (
              <li key={step.id} className="border-b border-rule">
                <button
                  type="button"
                  onClick={() => reachable && onJump(step.id, i)}
                  disabled={!reachable}
                  aria-current={active ? "step" : undefined}
                  className={cn(
                    "group grid w-full grid-cols-[2.25rem_1fr_auto] items-baseline gap-2 py-3 text-left transition-colors",
                    active ? "text-ink" : done ? "text-ink-soft hover:text-ink" : "text-ink-faint",
                    !reachable && "cursor-not-allowed"
                  )}
                >
                  <span className={cn("readout text-xs", active && "marker text-[hsl(30_12%_10%)]")}>
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  <span className="min-w-0">
                    <span className={cn("block text-sm", active ? "font-semibold" : "font-medium")}>{step.label}</span>
                    <span className="mt-0.5 block text-xs leading-snug text-ink-faint">{step.blurb}</span>
                  </span>
                  {done && <Check className="h-3.5 w-3.5 text-ok" strokeWidth={2.5} aria-label="done" />}
                </button>
              </li>
            );
          })}
        </ol>
      </div>
    </nav>
  );
}

/** Each step opens like a section of the record. */
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
    <div className="animate-rise">
      <div className="mb-8 border-b border-rule pb-6">
        {badge && <p className="label mb-3">{badge}</p>}
        <h1 className="text-4xl leading-[1.05] md:text-[2.75rem]">{title}</h1>
        {intro && <p className="mt-3 max-w-2xl font-display text-lg italic leading-snug text-ink-soft">{intro}</p>}
      </div>
      <div className="space-y-10">{children}</div>
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
    <div className="space-y-4">
      <div>
        <h3 className="font-display text-xl font-normal leading-snug text-ink">{legend}</h3>
        {hint && <p className="mt-1 max-w-[62ch] text-sm leading-relaxed text-ink-faint">{hint}</p>}
      </div>
      <div>{children}</div>
    </div>
  );
}

/** Fitzpatrick scale. The swatches are content, so they keep their true colours. */
export const SKIN_TONES = [
  { type: 1, name: "Type I", desc: "Very fair, ivory. Always burns, freckles easily.", colors: "from-[#ffeedf] to-[#fce4d6]", border: "#f0d5c2" },
  { type: 2, name: "Type II", desc: "Fair, peach. Usually burns, tans with difficulty.", colors: "from-[#f5d5be] to-[#eccbb4]", border: "#deba9f" },
  { type: 3, name: "Type III", desc: "Medium, golden. Mild burn risk, tans gradually.", colors: "from-[#e2b79a] to-[#d4a889]", border: "#c59877" },
  { type: 4, name: "Type IV", desc: "Olive, light brown. Rarely burns, tans easily.", colors: "from-[#c6906e] to-[#b77f5c]", border: "#a86e49" },
  { type: 5, name: "Type V", desc: "Brown, rich bronze. Very rarely burns, tans deeply.", colors: "from-[#9a6442] to-[#885433]", border: "#774526" },
  { type: 6, name: "Type VI", desc: "Deep brown / ebony. Never burns, deeply pigmented.", colors: "from-[#5d3b2a] to-[#4c2d1d]", border: "#3d2214" },
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
      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {SKIN_TONES.map((tone) => {
          const selected = value === tone.type;
          return (
            <button
              key={tone.type}
              type="button"
              onClick={() => onChange(tone.type)}
              aria-pressed={selected}
              className={cn(
                "relative flex items-start gap-3.5 rounded border p-3.5 text-left transition-colors",
                selected ? SELECTED : UNSELECTED
              )}
            >
              <span
                className={cn("h-10 w-10 shrink-0 rounded-full border bg-gradient-to-br", tone.colors)}
                style={{ borderColor: tone.border }}
              />
              <span className="min-w-0 flex-1">
                <span className="flex items-center justify-between gap-1">
                  <span className="readout text-sm font-medium text-ink">{tone.name}</span>
                  {selected && <Check className="h-4 w-4 text-ink" strokeWidth={2.5} />}
                </span>
                <span className="mt-0.5 block text-xs leading-snug">{tone.desc}</span>
              </span>
            </button>
          );
        })}
      </div>

      <button
        type="button"
        onClick={() => onChange(null)}
        className={cn(
          "inline-flex items-center gap-1.5 rounded px-2 py-1 text-xs transition-colors",
          value === null ? "font-semibold text-ink" : "text-ink-faint hover:text-ink"
        )}
      >
        <HelpCircle className="h-3.5 w-3.5" />
        I&apos;d prefer not to answer
      </button>
    </div>
  );
}

export const PATTERNS = [
  { id: "receding", title: "Receding hairline", subtitle: "Thinning mainly at the temples or forehead line", badge: "Frontal" },
  { id: "crown", title: "Crown / vertex", subtitle: "Thinning or a bald spot at the top-back swirl", badge: "Vertex" },
  { id: "diffuse", title: "Overall diffuse", subtitle: "Even thinning across the whole scalp", badge: "All over" },
  { id: "patchy", title: "Patchy loss", subtitle: "Distinct round or oval bare spots that appeared suddenly", badge: "Focal" },
  { id: "unsure", title: "Prevention / unsure", subtitle: "Routine tracking, or no clear focus yet", badge: "Routine" },
];

export function PatternPicker({
  value,
  onChange,
}: {
  value: string | null;
  onChange: (id: string) => void;
}) {
  return (
    <div className="grid gap-2 sm:grid-cols-2">
      {PATTERNS.map((p) => {
        const selected = value === p.id;
        return (
          <button
            key={p.id}
            type="button"
            onClick={() => onChange(p.id)}
            aria-pressed={selected}
            className={cn("flex flex-col rounded border p-4 text-left transition-colors", selected ? SELECTED : UNSELECTED)}
          >
            <span className="flex items-baseline justify-between gap-2">
              <span className="font-display text-lg leading-tight text-ink">{p.title}</span>
              <span className="label">{p.badge}</span>
            </span>
            <span className="mt-1.5 text-sm leading-relaxed">{p.subtitle}</span>
          </button>
        );
      })}
    </div>
  );
}

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
    <div className="grid gap-2 sm:grid-cols-2 md:grid-cols-3">
      {options.map((o) => {
        const selected = value === o.value;
        return (
          <button
            key={o.value}
            type="button"
            onClick={() => onChange(o.value)}
            aria-pressed={selected}
            className={cn(
              "flex items-center justify-between gap-2 rounded border px-3.5 py-3 text-left transition-colors",
              selected ? SELECTED : UNSELECTED
            )}
          >
            <span>
              <span className={cn("text-sm", selected ? "font-semibold" : "font-medium")}>{o.label}</span>
              {o.description && <span className="mt-0.5 block text-xs text-ink-faint">{o.description}</span>}
            </span>
            {selected && <Check className="h-4 w-4 shrink-0" strokeWidth={2.5} />}
          </button>
        );
      })}
    </div>
  );
}

/** Multi-select: a ticked item reads as stamped, ink on paper. */
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
      aria-pressed={checked}
      className={cn(
        "inline-flex items-center gap-2 rounded border px-3 py-2 text-sm transition-colors",
        checked ? "border-ink bg-ink text-ground" : "border-rule-strong bg-surface text-ink hover:bg-surface-sunken"
      )}
    >
      <span
        className={cn(
          "flex h-4 w-4 items-center justify-center rounded-sm border",
          checked ? "border-marker bg-marker text-[hsl(30_12%_10%)]" : "border-ink-faint"
        )}
      >
        {checked && <Check className="h-3 w-3" strokeWidth={3} />}
      </span>
      {label}
    </button>
  );
}

export function MedicationInput({
  medications,
  onChange,
}: {
  medications: string[];
  onChange: (meds: string[]) => void;
}) {
  const [input, setInput] = React.useState("");

  const POPULAR_MEDS = ["Minoxidil", "Finasteride", "Biotin", "Iron supplement", "Multivitamin", "Levothyroxine"];

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
    <div className="space-y-4">
      {medications.length > 0 && (
        <ul className="flex flex-wrap gap-2">
          {medications.map((m) => (
            <li
              key={m}
              className="inline-flex items-center gap-1.5 rounded-sm border border-ink bg-surface py-1 pl-2.5 pr-1 font-mono text-xs"
            >
              {m}
              <button
                type="button"
                onClick={() => removeMed(m)}
                className="rounded-sm p-0.5 text-ink-faint hover:bg-surface-sunken hover:text-ink"
                aria-label={`Remove ${m}`}
              >
                <X className="h-3 w-3" />
              </button>
            </li>
          ))}
        </ul>
      )}

      <div className="flex max-w-md gap-2">
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
          placeholder="Type a medication and press Enter"
          className="flex-1 rounded border border-rule-strong bg-surface px-3.5 py-2.5 text-sm placeholder:text-ink-faint focus:border-ink focus:outline-none focus:ring-2 focus:ring-marker/70"
        />
        <button
          type="button"
          onClick={() => addMed(input)}
          className="rounded border border-ink px-4 text-sm font-semibold transition-colors hover:border-marker hover:bg-marker hover:text-[hsl(30_12%_10%)]"
        >
          Add
        </button>
      </div>

      <div>
        <p className="label mb-2">Commonly reported</p>
        <div className="flex flex-wrap gap-1.5">
          {POPULAR_MEDS.filter((p) => !medications.includes(p)).map((item) => (
            <button
              key={item}
              type="button"
              onClick={() => addMed(item)}
              className="inline-flex items-center gap-1 rounded-sm border border-dashed border-rule-strong px-2 py-1 text-xs text-ink-soft transition-colors hover:border-ink hover:text-ink"
            >
              <Plus className="h-3 w-3" />
              {item}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
