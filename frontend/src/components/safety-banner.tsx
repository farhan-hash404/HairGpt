import { AlertTriangle, CheckCircle2, Stethoscope } from "lucide-react";
import { cn } from "@/lib/utils";

export type SafetyVerdict = {
  verdict: "ok" | "caution" | "refer";
  red_flags: string[];
  suppressed_cosmetic: boolean;
  message: string;
};

/**
 * When the deterministic safety layer returns "refer", this banner dominates the
 * screen and cosmetic recommendations are not rendered at all (the API does not
 * even return them).
 */
export function SafetyBanner({ verdict }: { verdict: SafetyVerdict }) {
  const map = {
    ok: {
      icon: CheckCircle2,
      tone: "border-primary/30 bg-primary/5 text-foreground",
      iconTone: "text-primary",
      title: "No red flags detected",
    },
    caution: {
      icon: AlertTriangle,
      tone: "border-[hsl(var(--caution))]/40 bg-[hsl(var(--caution))]/10 text-foreground",
      iconTone: "text-[hsl(var(--caution))]",
      title: "Interpret with caution",
    },
    refer: {
      icon: Stethoscope,
      tone: "border-destructive/40 bg-destructive/10 text-foreground",
      iconTone: "text-destructive",
      title: "Please see a clinician",
    },
  } as const;

  const cfg = map[verdict.verdict] ?? map.caution;
  const Icon = cfg.icon;

  return (
    <div className={cn("rounded-[var(--radius)] border p-5", cfg.tone)} role="status">
      <div className="flex items-start gap-3">
        <Icon className={cn("mt-0.5 h-5 w-5 shrink-0", cfg.iconTone)} />
        <div className="min-w-0">
          <p className="font-semibold">{cfg.title}</p>
          <p className="mt-1 text-sm text-muted-foreground">{verdict.message}</p>
          {verdict.suppressed_cosmetic && (
            <p className="mt-2 text-sm font-medium">
              Self-treatment suggestions are intentionally withheld for this result.
            </p>
          )}
          {!!verdict.red_flags?.length && (
            <ul className="mt-2 flex flex-wrap gap-1.5">
              {verdict.red_flags.map((f) => (
                <li key={f} className="rounded-full border border-current/20 px-2 py-0.5 text-xs">
                  {f.replace(/_/g, " ")}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
