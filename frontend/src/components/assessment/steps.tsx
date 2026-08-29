"use client";

import * as React from "react";
import { Check } from "lucide-react";
import { cn } from "@/lib/utils";

export type StepId = "profile" | "story" | "health" | "safety" | "capture" | "reading";

export const STEPS: { id: StepId; label: string; blurb: string }[] = [
  { id: "profile", label: "About you", blurb: "Used only to report accuracy per group" },
  { id: "story", label: "Your hair story", blurb: "Onset, pattern, how long" },
  { id: "health", label: "Health context", blurb: "What a photo cannot show" },
  { id: "safety", label: "Safety check", blurb: "Signs that need a clinician" },
  { id: "capture", label: "Seven views", blurb: "Guided, quality-gated capture" },
  { id: "reading", label: "The reading", blurb: "Observations and confidence" },
];

/** A numbered rail. The numbering is load-bearing here: this genuinely is a
 *  sequence, and history must be taken before capture for the reading to mean
 *  anything — which is the whole argument for the flow existing. */
export function StepRail({
  current,
  furthest,
  onJump,
}: {
  current: StepId;
  furthest: number;
  onJump: (id: StepId, index: number) => void;
}) {
  const currentIndex = STEPS.findIndex((s) => s.id === current);

  return (
    <nav aria-label="Assessment progress">
      {/* Compact rail on small screens */}
      <ol className="flex items-center gap-1.5 lg:hidden">
        {STEPS.map((step, i) => (
          <li key={step.id} className="flex-1">
            <span
              className={cn(
                "block h-1 rounded",
                i < currentIndex ? "bg-accent" : i === currentIndex ? "bg-accent" : "bg-rule"
              )}
            />
          </li>
        ))}
      </ol>
      <p className="mt-2 text-sm lg:hidden">
        <span className="readout text-ink-faint">
          {String(currentIndex + 1).padStart(2, "0")}/{STEPS.length}
        </span>{" "}
        <span className="font-medium">{STEPS[currentIndex]?.label}</span>
      </p>

      {/* Full rail on desktop */}
      <ol className="hidden lg:block">
        {STEPS.map((step, i) => {
          const done = i < currentIndex;
          const active = i === currentIndex;
          const reachable = i <= furthest;

          return (
            <li key={step.id}>
              <button
                onClick={() => reachable && onJump(step.id, i)}
                disabled={!reachable}
                aria-current={active ? "step" : undefined}
                className={cn(
                  "flex w-full gap-3 border-l-2 py-2.5 pl-4 text-left transition-colors",
                  active
                    ? "border-accent"
                    : done
                      ? "border-accent/35 hover:border-accent/60"
                      : "border-rule",
                  !reachable && "cursor-default opacity-45"
                )}
              >
                <span
                  className={cn(
                    "readout mt-0.5 text-xs",
                    active ? "text-accent" : done ? "text-ink-soft" : "text-ink-faint"
                  )}
                >
                  {done ? <Check className="h-3.5 w-3.5" aria-hidden="true" /> : String(i + 1).padStart(2, "0")}
                </span>
                <span className="min-w-0">
                  <span className={cn("block text-sm", active ? "font-medium text-ink" : "text-ink-soft")}>
                    {step.label}
                  </span>
                  <span className="mt-0.5 block text-xs text-ink-faint">{step.blurb}</span>
                </span>
              </button>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}

/** Consistent frame for a step's content. */
export function StepPanel({
  title,
  intro,
  children,
}: {
  title: string;
  intro?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="animate-rise">
      <h1 className="text-2xl font-normal">{title}</h1>
      {intro && <p className="mt-2 max-w-[62ch] text-sm text-ink-soft">{intro}</p>}
      <div className="mt-6 space-y-6">{children}</div>
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
    <fieldset className="border-t pt-4">
      <legend className="label -mt-[1.4rem] bg-ground pr-3">{legend}</legend>
      {hint && <p className="mb-3 max-w-[62ch] text-xs text-ink-faint">{hint}</p>}
      <div className="space-y-2">{children}</div>
    </fieldset>
  );
}

export function ChoiceGroup({
  value,
  options,
  onChange,
}: {
  value: string | null;
  options: { value: string; label: string }[];
  onChange: (v: string) => void;
}) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          onClick={() => onChange(o.value)}
          aria-pressed={value === o.value}
          className={cn(
            "rounded border px-3 py-1.5 text-sm transition-colors",
            value === o.value
              ? "border-accent bg-accent-wash text-accent"
              : "border-rule text-ink-soft hover:border-rule-strong hover:text-ink"
          )}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

export function CheckRow({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <label
      className={cn(
        "flex cursor-pointer items-center gap-3 rounded border px-3 py-2.5 text-sm transition-colors",
        checked ? "border-accent-edge bg-accent-wash" : "border-rule hover:border-rule-strong"
      )}
    >
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="h-4 w-4 accent-[hsl(var(--accent))]"
      />
      {label}
    </label>
  );
}
