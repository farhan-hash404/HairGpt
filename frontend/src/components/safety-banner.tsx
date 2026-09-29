import { AlertTriangle, Check, Stethoscope } from "lucide-react";
import { cn } from "@/lib/utils";

export type SafetyVerdict = {
  verdict: "ok" | "caution" | "refer";
  red_flags: string[];
  suppressed_cosmetic: boolean;
  message: string;
};

/**
 * The safety verdict, given a severity stripe rather than a tinted card.
 *
 * When the deterministic layer returns "refer" this must dominate the screen —
 * and the API has already withheld every cosmetic recommendation, so the banner
 * states that plainly instead of leaving the reader to notice an absence.
 */
export function SafetyBanner({ verdict }: { verdict: SafetyVerdict }) {
  const config = {
    ok: {
      icon: Check,
      stripe: "bg-ok",
      tint: "bg-ok-wash",
      tone: "text-ok",
      title: "No red flags detected",
    },
    caution: {
      icon: AlertTriangle,
      stripe: "bg-caution",
      tint: "bg-caution-wash",
      tone: "text-caution",
      title: "Interpret with caution",
    },
    refer: {
      icon: Stethoscope,
      stripe: "bg-alert",
      tint: "bg-alert-wash",
      tone: "text-alert",
      title: "See a clinician",
    },
  }[verdict.verdict] ?? {
    icon: AlertTriangle,
    stripe: "bg-caution",
    tint: "bg-caution-wash",
    tone: "text-caution",
    title: "Interpret with caution",
  };

  const Icon = config.icon;

  return (
    <div className={cn("panel flex overflow-hidden", config.tint)} role="status">
      <span className={cn("w-1 shrink-0", config.stripe)} aria-hidden="true" />
      <div className="flex flex-1 items-start gap-3 p-4">
        <Icon className={cn("mt-0.5 h-4 w-4 shrink-0", config.tone)} aria-hidden="true" />
        <div className="min-w-0 flex-1">
          <p className={cn("font-display text-base font-medium", config.tone)}>{config.title}</p>
          <p className="mt-1 max-w-[68ch] text-sm text-ink-soft">{verdict.message}</p>

          {verdict.suppressed_cosmetic && (
            <p className="mt-2 text-sm font-medium">
              Self-treatment suggestions are withheld for this result.
            </p>
          )}

          {!!verdict.red_flags?.length && (
            <ul className="mt-3 flex flex-wrap gap-1.5">
              {verdict.red_flags.map((flag) => (
                <li
                  key={flag}
                  className="readout rounded-sm border border-rule-strong px-1.5 py-0.5 text-2xs text-ink-soft"
                >
                  {flag.replace(/^history_/, "").replace(/_/g, " ")}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
