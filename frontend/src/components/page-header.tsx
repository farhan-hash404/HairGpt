import * as React from "react";

import { cn } from "@/lib/utils";

/* Every page opens like a journal section: a numbered instrument label, a
   serif headline, and a one-line italic dek. */
export function PageHeader({
  index,
  eyebrow,
  title,
  dek,
  actions,
  className,
}: {
  index?: string;
  eyebrow: string;
  title: React.ReactNode;
  dek?: React.ReactNode;
  actions?: React.ReactNode;
  className?: string;
}) {
  return (
    <header className={cn("mb-8 border-b border-rule pb-6 md:mb-10 md:pb-8", className)}>
      <div className="flex flex-wrap items-end justify-between gap-x-8 gap-y-5">
        <div className="max-w-3xl">
          <p className="label mb-4 flex items-center gap-2">
            {index && <span className="text-ink">{index}</span>}
            {index && <span aria-hidden="true" className="h-px w-6 bg-rule-strong" />}
            <span>{eyebrow}</span>
          </p>
          <h1 className="text-4xl leading-[1.02] md:text-5xl">{title}</h1>
          {dek && <p className="mt-4 max-w-[62ch] font-display text-lg italic leading-snug text-ink-soft">{dek}</p>}
        </div>
        {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
      </div>
    </header>
  );
}
