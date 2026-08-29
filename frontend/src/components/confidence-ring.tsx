import { cn } from "@/lib/utils";

/**
 * Confidence is a first-class citizen in this product: every AI number is shown
 * with the system's confidence in it. Never hidden behind hover.
 */
export function ConfidenceRing({
  value,
  size = 44,
  label,
  className,
}: {
  value: number; // 0..1
  size?: number;
  label?: string;
  className?: string;
}) {
  const v = Math.max(0, Math.min(1, value ?? 0));
  const stroke = 4;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const tone = v >= 0.7 ? "text-primary" : v >= 0.45 ? "text-[hsl(var(--caution))]" : "text-muted-foreground";

  return (
    <div
      className={cn("relative inline-flex shrink-0 items-center justify-center", className)}
      role="img"
      aria-label={`Confidence ${Math.round(v * 100)} percent${label ? ` for ${label}` : ""}`}
    >
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          strokeWidth={stroke}
          className="stroke-muted"
          fill="none"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={`${c * v} ${c}`}
          className={cn("fill-none transition-all duration-700", tone)}
          stroke="currentColor"
        />
      </svg>
      <span className="absolute text-[10px] font-semibold tabular-nums">{Math.round(v * 100)}</span>
    </div>
  );
}
