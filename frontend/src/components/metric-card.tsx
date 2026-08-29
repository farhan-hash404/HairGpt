import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { ConfidenceRing } from "@/components/confidence-ring";
import { cn } from "@/lib/utils";

export function MetricCard({
  label,
  value,
  sublabel,
  confidence,
  isMock,
  href,
  tone = "default",
}: {
  label: string;
  value: string;
  sublabel?: string;
  confidence?: number | null;
  isMock?: boolean;
  href?: string;
  tone?: "default" | "muted";
}) {
  const inner = (
    <Card
      className={cn(
        "flex h-full items-start justify-between gap-3 p-5 transition-shadow",
        href && "hover:shadow-md",
        tone === "muted" && "bg-muted/40"
      )}
    >
      <div className="min-w-0">
        <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</p>
        {/* Long qualitative labels (e.g. "crown appears sparse") get a smaller
            size and wrap instead of being cut off mid-word. */}
        <p className={cn("metric-number mt-1.5 break-words", value.length > 14 && "text-xl leading-snug")}>
          {value}
        </p>
        {sublabel && <p className="mt-1 text-sm text-muted-foreground">{sublabel}</p>}
        {isMock && (
          <Badge variant="mock" className="mt-2">
            mock model · not validated
          </Badge>
        )}
      </div>
      {confidence !== undefined && confidence !== null && (
        <ConfidenceRing value={confidence} label={label} />
      )}
    </Card>
  );

  return href ? (
    <Link href={href} className="block h-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-[var(--radius)]">
      {inner}
    </Link>
  ) : (
    inner
  );
}
