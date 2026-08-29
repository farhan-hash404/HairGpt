import { cn } from "@/lib/utils";

/**
 * Confidence, drawn as a measurement scale.
 *
 * This product's whole argument is that it is candid about its own uncertainty,
 * so confidence gets the visual treatment of an instrument readout rather than
 * a dashboard donut: a ruled track with quarter ticks, a filled span, and the
 * value in mono. Ticks matter — they tell the reader the number sits on a scale
 * with a floor and a ceiling, which a bare percentage does not.
 *
 * Banding is deliberately blunt. Below 45% the product says so in words rather
 * than colouring a bar slightly differently and hoping the reader notices.
 */

export type ConfidenceBand = "low" | "moderate" | "high";

export function bandOf(value: number): ConfidenceBand {
  if (value >= 0.7) return "high";
  if (value >= 0.45) return "moderate";
  return "low";
}

const BAND_COPY: Record<ConfidenceBand, string> = {
  high: "high",
  moderate: "moderate",
  low: "low — interpret with caution",
};

/**
 * Confidence is deliberately NOT colour-coded with the semantic states.
 *
 * Painting low confidence red would read as "something is wrong with your hair"
 * when it actually means "we are unsure". Those are different messages, and
 * conflating them is precisely the miscommunication this product exists to
 * avoid. Semantic colour is reserved for the safety verdict.
 *
 * Instead, certainty is encoded in the FILL ITSELF: solid where the reading is
 * firm, hatched where it is provisional. A hatched bar reads as "incomplete"
 * rather than "danger", which is the honest signal.
 */
const BAND_FILL: Record<ConfidenceBand, string> = {
  high: "bg-accent",
  moderate: "bg-accent/65",
  low: "bg-accent/45 [background-image:repeating-linear-gradient(135deg,transparent_0_3px,hsl(var(--surface))_3px_5px)]",
};

export function ConfidenceScale({
  value,
  label,
  size = "default",
  showBand = true,
  className,
}: {
  value: number;
  /** What the confidence is about, for screen readers. */
  label?: string;
  size?: "sm" | "default";
  showBand?: boolean;
  className?: string;
}) {
  const v = Math.max(0, Math.min(1, value ?? 0));
  const band = bandOf(v);
  const pct = Math.round(v * 100);

  return (
    <div className={cn("min-w-0", className)}>
      <div className="flex items-baseline justify-between gap-3">
        <span className="label">Confidence</span>
        <span
          className={cn("readout font-medium", size === "sm" ? "text-xs" : "text-sm")}
          aria-hidden="true"
        >
          {pct}%
        </span>
      </div>

      <div
        className={cn("relative mt-1.5 w-full overflow-hidden rounded-[2px] bg-surface-sunken", size === "sm" ? "h-1.5" : "h-2")}
        role="meter"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`Confidence ${pct} percent${label ? ` for ${label}` : ""}, ${band}`}
      >
        <div
          className={cn("h-full origin-left animate-sweep", BAND_FILL[band])}
          style={{ width: `${pct}%` }}
        />
        {/* Quarter ticks: the value sits on a scale, not in a vacuum. */}
        <div className="pointer-events-none absolute inset-0 flex justify-between px-0">
          {[0, 1, 2, 3, 4].map((i) => (
            <span key={i} className="w-px bg-rule-strong/60" />
          ))}
        </div>
      </div>

      {showBand && (
        <p className={cn("mt-1 text-ink-faint", size === "sm" ? "text-2xs" : "text-xs")}>
          {BAND_COPY[band]}
        </p>
      )}
    </div>
  );
}

/** Compact inline variant for dense rows, where a full scale would crowd. */
export function ConfidenceChip({ value, className }: { value: number; className?: string }) {
  const v = Math.max(0, Math.min(1, value ?? 0));
  const band = bandOf(v);
  return (
    <span
      className={cn("inline-flex items-center gap-1.5 whitespace-nowrap", className)}
      title={`Confidence ${Math.round(v * 100)}% (${band})`}
    >
      <span className="relative h-1.5 w-10 overflow-hidden rounded-[2px] bg-surface-sunken">
        <span className={cn("absolute inset-y-0 left-0", BAND_FILL[band])} style={{ width: `${v * 100}%` }} />
      </span>
      <span className="readout text-2xs text-ink-soft">{Math.round(v * 100)}%</span>
    </span>
  );
}
