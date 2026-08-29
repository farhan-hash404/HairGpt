import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

/* Badges encode state, not decoration. Semantic variants are separate from the
   accent so severity never competes with brand emphasis; `flag` is dashed to
   read as a caveat rather than a status. */
const badgeVariants = cva(
  "inline-flex items-center gap-1 rounded border px-1.5 py-0.5 text-2xs font-semibold uppercase tracking-[0.07em]",
  {
    variants: {
      variant: {
        default: "border-accent-edge bg-accent-wash text-accent",
        neutral: "border-rule bg-surface-sunken text-ink-soft",
        ok: "border-transparent bg-ok-wash text-ok",
        caution: "border-transparent bg-caution-wash text-caution",
        alert: "border-transparent bg-alert-wash text-alert",
        flag: "border-dashed border-rule-strong bg-transparent text-ink-faint",
      },
    },
    defaultVariants: { variant: "default" },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
