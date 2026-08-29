"use client";

import * as React from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { FileText, Stethoscope } from "lucide-react";
import { api, modelTrustLabel, type Analysis, type Observation } from "@/lib/api";
import { AuthGate } from "@/components/auth-gate";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ConfidenceChip, ConfidenceScale } from "@/components/confidence";
import { SafetyBanner } from "@/components/safety-banner";
import { WhyEvidence } from "@/components/why-evidence";
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

    const display = label
      ? label
      : mean !== null
        ? `${mean.toFixed(3)}${unit ? ` ${unit}` : ""}`
        : "—";

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

  if (error) return <p className="text-alert">{error}</p>;
  if (!data) return <p className="text-ink-soft">Loading your analysis…</p>;

  const referred = data.safety_verdict?.verdict === "refer";

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-ink-soft">
            {data.domain === "hair" ? "Hair & scalp analysis" : "Skin analysis"}
          </p>
          <h1 className="mt-1 text-2xl font-normal">Your results</h1>
          <p className="mt-1 text-sm text-ink-soft">{data.explanation?.summary}</p>
        </div>
        <div className="flex items-center gap-3">
          <ConfidenceScale value={data.overall_confidence} label="overall" className="w-40" />
          <div className="text-sm">
            <p className="font-medium">Overall confidence</p>
            <p className="text-ink-soft">
              {data.overall_confidence < 0.5 ? "low — interpret cautiously" : "moderate"}
            </p>
          </div>
        </div>
      </header>

      {data.safety_verdict && <SafetyBanner verdict={data.safety_verdict} />}

      {data.skin_appearance_index !== null && data.skin_appearance_index !== undefined && (
        <Card>
          <CardHeader>
            <CardTitle>Skin Appearance Index</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="readout-lg">{data.skin_appearance_index}</p>
            <p className="mt-1 text-sm text-ink-soft">
              A transparent composite of apparent attributes (0–100). Not a clinical score.
            </p>
          </CardContent>
        </Card>
      )}

      {/* Observations — aggregated across views, with the per-view spread shown
          so a single number never hides disagreement between images. */}
      <section>
        <h2 className="mb-3 text-lg font-medium">What the images appear to show</h2>
        <div className="grid gap-3 sm:grid-cols-2">
          {groupObservations(data.observations).map((g) => (
            <Card key={g.kind} className="p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="font-medium">{titleize(g.kind)}</p>
                  <p className="mt-0.5 text-sm text-ink-soft">{g.display}</p>
                  {g.count > 1 && (
                    <p className="mt-0.5 text-xs text-ink-soft">
                      across {g.count} views
                      {g.spread !== null && ` · range ${g.min?.toFixed(3)}–${g.max?.toFixed(3)}`}
                    </p>
                  )}
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    <Badge variant={g.observationType === "visual_observation" ? "neutral" : "default"}>
                      {g.observationType === "visual_observation" ? "visual observation" : "AI inference"}
                    </Badge>
                    {(() => {
                      const trust = modelTrustLabel({ is_mock: g.isMock, validated: g.validated });
                      return trust ? <Badge variant={trust.variant}>{trust.text}</Badge> : null;
                    })()}
                  </div>
                  <p className="mt-2 text-xs text-ink-soft">{g.basis}</p>
                </div>
                <ConfidenceChip value={g.confidence} />
              </div>
            </Card>
          ))}
        </div>
      </section>

      {/* Recommendations — suppressed entirely when the safety layer says refer */}
      <section>
        <h2 className="mb-3 text-lg font-medium">
          {referred ? "Next step" : "Suggested next steps"}
        </h2>
        <div className="space-y-3">
          {data.recommendations.map((r, i) => (
            <Card key={i}>
              <CardContent className="pt-5">
                <div className="mb-2 flex flex-wrap items-center gap-2">
                  <Badge variant={r.type === "referral" ? "alert" : r.requires_clinician ? "caution" : "default"}>
                    {titleize(r.type)}
                  </Badge>
                  {r.requires_clinician && (
                    <span className="inline-flex items-center gap-1 text-xs text-ink-soft">
                      <Stethoscope className="h-3 w-3" /> clinician involvement recommended
                    </span>
                  )}
                </div>
                <p className="font-medium">{r.title}</p>
                <p className="mt-1 text-sm text-ink-soft">{r.body}</p>
                <div className="mt-3">
                  <WhyEvidence
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
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      <div className="flex flex-wrap gap-3">
        <Link href={`/report/${data.session_id}`}>
          <Button variant="outline">
            <FileText className="h-4 w-4" /> Doctor report
          </Button>
        </Link>
        <Link href="/compare">
          <Button variant="outline">Compare with previous scan</Button>
        </Link>
        <Link href="/timeline">
          <Button variant="outline">Treatment timeline</Button>
        </Link>
      </div>

      <Card className="bg-surface-sunken">
        <CardContent className="pt-5">
          <p className="mb-2 text-sm font-medium">Limitations &amp; disclaimers</p>
          <ul className="space-y-1 text-xs text-ink-soft">
            {[...(data.explanation?.limitations ?? []), ...data.disclaimers].map((d, i) => (
              <li key={i}>• {d}</li>
            ))}
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
