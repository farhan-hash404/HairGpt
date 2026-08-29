import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { ConfidenceScale } from "@/components/confidence";
import { cn } from "@/lib/utils";

/**
 * A single instrument readout.
 *
 * The hierarchy is deliberate and inverted from a typical dashboard card: the
 * field name is small, the measurement is large and set in mono, and the
 * confidence sits directly beneath it rather than being tucked in a corner.
 * A number this product cannot stand behind should never appear more
 * authoritative than the caveat attached to it.
 */
export function Readout({
  label,
  value,
  unit,
  caption,
  confidence,
  flag,
  href,
  className,
}: {
  label: string;
  value: string;
  unit?: string;
  caption?: string;
  confidence?: number | null;
  /** e.g. "unvalidated model" — rendered as a dashed caveat, not a status. */
  flag?: string | null;
  href?: string;
  className?: string;
}) {
  const body = (
    <div
      className={cn(
        "group flex h-full flex-col gap-3 p-4",
        href && "transition-colors hover:bg-surface-sunken",
        className
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <span className="label">{label}</span>
        {href && (
          <ArrowUpRight className="h-3.5 w-3.5 shrink-0 text-ink-faint opacity-0 transition-opacity group-hover:opacity-100" />
        )}
      </div>

      <div className="flex-1">
        <p className="readout-lg break-words">
          {value}
          {unit && <span className="ml-1 text-base font-normal text-ink-faint">{unit}</span>}
        </p>
        {caption && <p className="mt-1 text-xs leading-snug text-ink-soft">{caption}</p>}
        {flag && (
          <Badge variant="flag" className="mt-2">
            {flag}
          </Badge>
        )}
      </div>

      {confidence !== undefined && confidence !== null && (
        <ConfidenceScale value={confidence} label={label} size="sm" showBand={false} />
      )}
    </div>
  );

  if (!href) return <div className="panel h-full">{body}</div>;

  return (
    <Link href={href} className="panel block h-full rounded-lg">
      {body}
    </Link>
  );
}
