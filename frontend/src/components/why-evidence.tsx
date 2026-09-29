"use client";

import * as React from "react";
import { X } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Link001 } from "@/components/ui/skiper-ui/skiper40";
import { ConfidenceScale } from "@/components/confidence";
import { cn } from "@/lib/utils";

export type EvidenceRef = {
  id: string;
  source: string;
  title: string;
  url: string;
  publisher: string;
  evidence_grade: string;
};

export type Explain = {
  observation?: string;
  reasoning?: string;
  confidence?: { value: number; basis: string; method: string };
  limitations?: string[];
};

/**
 * Every major AI conclusion exposes its reasoning and its sources.
 *
 * These are rendered as plain text buttons rather than pill buttons: they are
 * disclosure controls on a document, and making them look like calls to action
 * would compete with the actual next steps on the page.
 */
export function WhyEvidence({
  explain,
  evidence,
  className,
}: {
  explain?: Explain;
  evidence?: EvidenceRef[];
  className?: string;
}) {
  const [open, setOpen] = React.useState<"why" | "evidence" | null>(null);

  const tab = (id: "why" | "evidence", label: string, count?: number) => (
    <button
      onClick={() => setOpen(open === id ? null : id)}
      aria-expanded={open === id}
      className={cn(
        "border-b-2 pb-1 text-sm transition-colors",
        open === id ? "border-accent text-ink" : "border-transparent text-ink-soft hover:text-ink"
      )}
    >
      {label}
      {count !== undefined && count > 0 && (
        <span className="readout ml-1.5 text-2xs text-ink-faint">{count}</span>
      )}
    </button>
  );

  return (
    <div className={className}>
      <div className="flex items-center gap-5">
        {tab("why", "Why?")}
        {tab("evidence", "Evidence", evidence?.length ?? 0)}
      </div>

      {open === "why" && (
        <Panel onClose={() => setOpen(null)}>
          {explain?.observation && (
            <Field name="Observation">
              <span className="whitespace-pre-line">{explain.observation}</span>
            </Field>
          )}
          {explain?.reasoning && <Field name="Reasoning">{explain.reasoning}</Field>}
          {explain?.confidence && (
            <Field name="Confidence">
              <ConfidenceScale value={explain.confidence.value} showBand={false} className="max-w-xs" />
              <p className="mt-1 text-xs text-ink-faint">{explain.confidence.basis}</p>
            </Field>
          )}
          {!!explain?.limitations?.length && (
            <Field name="Limitations">
              <ul className="space-y-1">
                {explain.limitations.map((l, i) => (
                  <li key={i} className="flex gap-2">
                    <span aria-hidden="true" className="text-ink-faint">
                      —
                    </span>
                    <span>{l}</span>
                  </li>
                ))}
              </ul>
            </Field>
          )}
        </Panel>
      )}

      {open === "evidence" && (
        <Panel onClose={() => setOpen(null)}>
          {evidence?.length ? (
            <ul className="divide-y">
              {evidence.map((e) => (
                <li key={e.id} className="py-3 first:pt-0 last:pb-0">
                  <div className="mb-1.5 flex flex-wrap items-center gap-1.5">
                    <Badge variant="neutral">{e.source.replace(/_/g, " ")}</Badge>
                    {e.evidence_grade && e.evidence_grade !== e.source && (
                      <Badge variant="flag">{e.evidence_grade.replace(/_/g, " ")}</Badge>
                    )}
                  </div>
                  <Link001 href={e.url} className="inline-flex font-medium text-ink">
                    {e.title}
                  </Link001>
                  <p className="caption mt-1">{e.publisher}</p>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-ink-soft">
              No medical sources attached — this item is general wellness information, not medical evidence.
            </p>
          )}
          <p className="caption mt-4 border-t pt-3">
            Sources are limited to the NHS, MedlinePlus, NIAMS, DailyMed drug labels and open-access peer-reviewed
            reviews. Social media is never used.
          </p>
        </Panel>
      )}
    </div>
  );
}

function Panel({ onClose, children }: { onClose: () => void; children: React.ReactNode }) {
  return (
    <div className="mt-3 animate-rise border-l-2 border-accent-edge bg-surface-sunken p-4 text-sm">
      <div className="flex justify-end">
        <button
          onClick={onClose}
          aria-label="Close"
          className="-mr-1 -mt-1 rounded p-1 text-ink-faint hover:text-ink"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      </div>
      <div className="-mt-4 space-y-4">{children}</div>
    </div>
  );
}

function Field({ name, children }: { name: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="label mb-1.5">{name}</p>
      <div className="text-ink-soft [&_strong]:text-ink">{children}</div>
    </div>
  );
}
