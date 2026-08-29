"use client";

import * as React from "react";
import { BookOpen, HelpCircle, X } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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

function Panel({
  title,
  onClose,
  children,
}: {
  title: string;
  onClose: () => void;
  children: React.ReactNode;
}) {
  return (
    <div className="mt-3 animate-fade-up rounded-xl border bg-muted/40 p-4 text-sm">
      <div className="mb-2 flex items-center justify-between">
        <span className="font-medium">{title}</span>
        <button onClick={onClose} aria-label="Close" className="text-muted-foreground hover:text-foreground">
          <X className="h-4 w-4" />
        </button>
      </div>
      {children}
    </div>
  );
}

/**
 * Every major AI conclusion exposes "Why?" (observation, reasoning, confidence,
 * limitations) and "Evidence" (traceable medical sources). Required by design.
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

  return (
    <div className={cn("", className)}>
      <div className="flex flex-wrap gap-2">
        <Button
          size="sm"
          variant="outline"
          onClick={() => setOpen(open === "why" ? null : "why")}
          aria-expanded={open === "why"}
        >
          <HelpCircle className="h-3.5 w-3.5" /> Why?
        </Button>
        <Button
          size="sm"
          variant="outline"
          onClick={() => setOpen(open === "evidence" ? null : "evidence")}
          aria-expanded={open === "evidence"}
        >
          <BookOpen className="h-3.5 w-3.5" /> Evidence
          {evidence?.length ? <span className="ml-1 opacity-60">({evidence.length})</span> : null}
        </Button>
      </div>

      {open === "why" && (
        <Panel title="Why we're showing this" onClose={() => setOpen(null)}>
          {explain?.observation && (
            <p className="mb-2 whitespace-pre-line">
              <span className="font-medium">Observation: </span>
              {explain.observation}
            </p>
          )}
          {explain?.reasoning && (
            <p className="mb-2">
              <span className="font-medium">Reasoning: </span>
              {explain.reasoning}
            </p>
          )}
          {explain?.confidence && (
            <p className="mb-2">
              <span className="font-medium">Confidence: </span>
              {Math.round(explain.confidence.value * 100)}% — {explain.confidence.basis}
            </p>
          )}
          {!!explain?.limitations?.length && (
            <>
              <p className="font-medium">Limitations</p>
              <ul className="ml-4 list-disc text-muted-foreground">
                {explain.limitations.map((l, i) => (
                  <li key={i}>{l}</li>
                ))}
              </ul>
            </>
          )}
        </Panel>
      )}

      {open === "evidence" && (
        <Panel title="Sources behind this guidance" onClose={() => setOpen(null)}>
          {evidence?.length ? (
            <ul className="space-y-2">
              {evidence.map((e) => (
                <li key={e.id} className="rounded-lg border bg-background p-3">
                  <div className="mb-1 flex flex-wrap items-center gap-2">
                    <Badge variant="secondary">{e.source.replace(/_/g, " ")}</Badge>
                    {/* Only show the grade when it adds information beyond the source name. */}
                    {e.evidence_grade && e.evidence_grade !== e.source && (
                      <Badge variant="outline">{e.evidence_grade.replace(/_/g, " ")}</Badge>
                    )}
                  </div>
                  <a href={e.url} target="_blank" rel="noreferrer" className="font-medium underline-offset-2 hover:underline">
                    {e.title}
                  </a>
                  <div className="text-xs text-muted-foreground">{e.publisher}</div>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-muted-foreground">
              No medical sources attached — this item is general wellness information, not medical evidence.
            </p>
          )}
          <p className="mt-3 text-xs text-muted-foreground">
            Sources are limited to AAD, FDA, NICE, NHS, and peer-reviewed dermatology literature. Social media is never used.
          </p>
        </Panel>
      )}
    </div>
  );
}
