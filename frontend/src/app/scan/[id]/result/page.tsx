"use client";

import * as React from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { FileText, Layers, LineChart, Stethoscope } from "lucide-react";
import { api, modelTrustLabel, type Analysis, type Observation } from "@/lib/api";
import { AuthGate } from "@/components/auth-gate";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { ConfidenceChip, ConfidenceScale } from "@/components/confidence";
import { MetricTerm } from "@/components/metric-term";
import { PageHeader } from "@/components/page-header";
import { SafetyBanner } from "@/components/safety-banner";
import { WhyEvidence } from "@/components/why-evidence";
import { ReticleMark } from "@/components/wordmark";
import { titleize } from "@/lib/utils";

export default function ResultPage() {
  return (
    <AuthGate>
      <Result />
    </AuthGate>
  );
}

type ObservationGroup = {
  kind: string;
  display: string;
  count: number;
  min: number | null;
  max: number | null;
  spread: number | null;
  confidence: number;
  basis: string;
  isMock: boolean;
  validated: boolean;
  observationType: Observation["observation_type"];
};

/**
 * Each capture view produces its own observation of the same kind. Showing seven
 * near-identical "Scalp Visibility" rows is noise, so we aggregate per kind —
 * but we surface the per-view RANGE, because a single averaged number must not
 * conceal disagreement between images. Confidence is the most conservative
 * (minimum) of the contributing views, never the average.
 */
function groupObservations(observations: Observation[]): ObservationGroup[] {
  const byKind = new Map<string, Observation[]>();
  for (const o of observations) {
    const list = byKind.get(o.kind) ?? [];
    list.push(o);
    byKind.set(o.kind, list);
  }

  return [...byKind.entries()].map(([kind, list]) => {
    const nums = list.map((o) => o.value_num).filter((v): v is number => v !== null);
    const hasNums = nums.length > 0;
    const mean = hasNums ? nums.reduce((a, b) => a + b, 0) / nums.length : null;
    const min = hasNums ? Math.min(...nums) : null;
    const max = hasNums ? Math.max(...nums) : null;
    const unit = list.find((o) => o.unit)?.unit ?? "";
    const label = list.find((o) => o.value_label)?.value_label ?? null;

    let display = "—";
    if (label) {
      display = label;
    } else if (mean !== null) {
      if (kind.includes("visibility") || kind.includes("density") || (!unit && mean >= 0 && mean <= 1)) {
        display = `${(mean * 100).toFixed(1)}%`;
      } else {
        display = `${mean.toFixed(2)}${unit ? ` ${unit}` : ""}`;
      }
    }

    return {
      kind,
      display,
      count: list.length,
      min,
      max,
      spread: min !== null && max !== null ? max - min : null,
      // Be conservative: the group is only as trustworthy as its weakest view.
      confidence: Math.min(...list.map((o) => o.confidence)),
      basis: list[0].confidence_basis,
      isMock: list.some((o) => o.is_mock),
      // Validated only if EVERY contributing view came from a validated model.
      validated: list.every((o) => o.validated),
      observationType: list[0].observation_type,
    };
  });
}

function Result() {
  const { id } = useParams<{ id: string }>();
  const [data, setData] = React.useState<Analysis | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    api.result(id).then(setData).catch((e) => setError(e?.message ?? "Could not load result"));
  }, [id]);

  if (error) {
    return <p className="border-l-2 border-alert bg-alert-wash px-4 py-3 text-sm text-alert">{error}</p>;
  }
  if (!data) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center gap-3 text-ink-soft">
        <ReticleMark className="h-6 w-6 animate-spin text-ink [animation-duration:2.4s]" />
        <p className="label">Loading your analysis…</p>
      </div>
    );
  }

  const referred = data.safety_verdict?.verdict === "refer";
  const groups = groupObservations(data.observations);
  const notes = [...(data.explanation?.limitations ?? []), ...data.disclaimers];

  return (
    <div className="mx-auto max-w-5xl animate-rise">
      <PageHeader
        eyebrow={data.domain === "hair" ? "Result · hair & scalp" : "Result · skin"}
        title={
          <>
            What the photographs <span className="italic text-ink-soft">appear</span> to show.
          </>
        }
        dek="Observations, each with its own confidence. Nothing here is a diagnosis."
        actions={
          <div className="w-56">
            <ConfidenceScale value={data.overall_confidence} label="overall" />
          </div>
        }
      />

      {data.safety_verdict && <SafetyBanner verdict={data.safety_verdict} />}

      {data.skin_appearance_index !== null && data.skin_appearance_index !== undefined && (
        <section className="panel mt-8 p-5">
          <p className="label">Skin appearance index</p>
          <p className="readout-lg mt-2">{data.skin_appearance_index}</p>
          <p className="mt-1 text-sm text-ink-soft">
            A transparent composite of apparent attributes (0–100). Not a clinical score.
          </p>
        </section>
      )}

      <section className="mt-12">
        <h2 className="flex items-baseline gap-3 text-2xl">
          <span className="readout text-sm text-ink-faint">A.</span>
          Findings
        </h2>
        <p className="mt-1 text-sm text-ink-soft">
          Aggregated across views. The range shows where views disagree; confidence is the weakest view&apos;s.
        </p>

        <div className="mt-5 border-t border-ink">
          <div className="hidden grid-cols-[1.3fr_1fr_1fr_0.9fr] gap-4 border-b border-rule py-2 md:grid">
            {["Finding", "Reading", "Across views", "Confidence"].map((h) => (
              <span key={h} className="label">
                {h}
              </span>
            ))}
          </div>
          {groups.map((g) => {
            const trust = modelTrustLabel({ is_mock: g.isMock, validated: g.validated });
            return (
              <div
                key={g.kind}
                className="grid gap-x-4 gap-y-2 border-b border-rule py-4 md:grid-cols-[1.3fr_1fr_1fr_0.9fr] md:items-baseline"
              >
                <div className="min-w-0">
                  <p className="font-display text-lg leading-tight">
                    <MetricTerm kind={g.kind} />
                  </p>
                  <div className="mt-1.5 flex flex-wrap gap-1.5">
                    <Badge variant={g.observationType === "visual_observation" ? "neutral" : "default"}>
                      {g.observationType === "visual_observation" ? "visual observation" : "AI inference"}
                    </Badge>
                    {trust && <Badge variant={trust.variant}>{trust.text}</Badge>}
                  </div>
                </div>
                <p className="readout text-[0.95rem] text-ink">{g.display}</p>
                <p className="caption">
                  {g.count > 1 ? `${g.count} views` : "1 view"}
                  {g.spread !== null && g.count > 1 && (
                    <>
                      <br />
                      range {g.min?.toFixed(3)}–{g.max?.toFixed(3)}
                    </>
                  )}
                </p>
                <div>
                  <ConfidenceChip value={g.confidence} />
                  <p className="caption mt-1 md:max-w-[16rem]">{g.basis}</p>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      <section className="mt-12">
        <h2 className="flex items-baseline gap-3 text-2xl">
          <span className="readout text-sm text-ink-faint">B.</span>
          {referred ? "Next step" : "Suggested next steps"}
        </h2>
        <ol className="mt-5 border-t border-ink">
          {data.recommendations.map((r, i) => (
            <li key={i} className="grid gap-x-5 border-b border-rule py-6 md:grid-cols-[3rem_1fr]">
              <span className="readout pt-1 text-sm text-ink-faint">{String(i + 1).padStart(2, "0")}</span>
              <div className="min-w-0">
                <div className="mb-2 flex flex-wrap items-center gap-2">
                  <Badge variant={r.type === "referral" ? "alert" : r.requires_clinician ? "caution" : "neutral"}>
                    {titleize(r.type)}
                  </Badge>
                  {r.requires_clinician && (
                    <span className="inline-flex items-center gap-1 text-xs text-ink-soft">
                      <Stethoscope className="h-3 w-3" /> involve a clinician
                    </span>
                  )}
                </div>
                <p className="font-display text-xl leading-snug">{r.title}</p>
                <p className="mt-1.5 max-w-[68ch] text-sm leading-relaxed text-ink-soft">{r.body}</p>
                <WhyEvidence
                  className="mt-4"
                  explain={{
                    observation: r.title,
                    reasoning: r.body,
                    confidence: {
                      value: r.confidence,
                      basis: "evidence-gated recommendation",
                      method: "rec_v1",
                    },
                    limitations: data.explanation?.limitations,
                  }}
                  evidence={r.evidence}
                />
              </div>
            </li>
          ))}
        </ol>
      </section>

      <div className="mt-10 flex flex-wrap gap-2">
        <Link href={`/report/${data.session_id}`} className={buttonVariants()}>
          <FileText className="h-4 w-4" strokeWidth={1.75} /> Doctor report
        </Link>
        <Link href="/compare" className={buttonVariants({ variant: "outline" })}>
          <Layers className="h-4 w-4" strokeWidth={1.75} /> Compare with a previous scan
        </Link>
        <Link href="/timeline" className={buttonVariants({ variant: "outline" })}>
          <LineChart className="h-4 w-4" strokeWidth={1.75} /> Timeline
        </Link>
      </div>

      {notes.length > 0 && (
        <section className="mt-14 border-t border-rule pt-5">
          <p className="label mb-3">Notes &amp; limitations</p>
          <ol className="grid gap-x-10 gap-y-2 md:grid-cols-2">
            {notes.map((d, i) => (
              <li key={i} className="grid grid-cols-[1.5rem_1fr] text-xs leading-relaxed text-ink-soft">
                <span className="readout text-ink-faint">{i + 1}</span>
                <span>{d}</span>
              </li>
            ))}
          </ol>
        </section>
      )}
    </div>
  );
}
