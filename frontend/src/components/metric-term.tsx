"use client";

import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/skiper-ui/skiper101";
import { titleize } from "@/lib/utils";

/* What each measurement is, and what it is not. Every reading is an
   appearance in a photograph, never a follicle count or a diagnosis. */
export const METRIC_DEFINITIONS: Record<string, string> = {
  scalp_visibility:
    "Share of the frame where scalp shows through the hair. Lower means fuller coverage; lighting and parting move it.",
  apparent_density:
    "How densely strands appear to cover the scalp, on a 0–1 index. An appearance in the photo, not a follicle count.",
  apparent_coverage: "Fraction of the analysed region that hair appears to cover.",
  crown_density: "Apparent density at the crown swirl, read from the top and crown views.",
  hairline_position:
    "Where the frontal hairline sits in the standard view. Only comparable when the framing matches.",
};

/** A metric name with its definition on hover or focus (Skiper UI tooltip). */
export function MetricTerm({ kind, label, className }: { kind: string; label?: string; className?: string }) {
  const text = label ?? titleize(kind);
  const definition = METRIC_DEFINITIONS[kind];
  if (!definition) return <span className={className}>{text}</span>;
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <button
          type="button"
          className={`cursor-help text-left underline decoration-rule-strong decoration-dotted underline-offset-[5px] hover:decoration-ink ${className ?? ""}`}
        >
          {text}
        </button>
      </TooltipTrigger>
      <TooltipContent side="top" sideOffset={6}>
        {definition}
      </TooltipContent>
    </Tooltip>
  );
}
