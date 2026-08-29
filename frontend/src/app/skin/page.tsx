"use client";

import * as React from "react";
import Link from "next/link";
import { ScanFace, Sun, Moon } from "lucide-react";
import { api, modelTrustLabel, type Analysis } from "@/lib/api";
import { AuthGate } from "@/components/auth-gate";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ConfidenceChip, ConfidenceScale } from "@/components/confidence";
import { Readout } from "@/components/metric-card";
import { SafetyBanner } from "@/components/safety-banner";
import { WhyEvidence } from "@/components/why-evidence";
import { titleize } from "@/lib/utils";

export default function SkinPage() {
  return (
    <AuthGate>
      <SkinDashboard />
    </AuthGate>
  );
}

function SkinDashboard() {
  const [latest, setLatest] = React.useState<Analysis | null>(null);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    (async () => {
      try {
        const list = await api.listScans();
        const skin = list.find((s: any) => s.domain === "skin" && s.status === "complete");
        if (skin) setLatest(await api.result(skin.id));
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  if (loading) return <p className="text-ink-soft">Loading SkinGPT…</p>;

  if (!latest)
    return (
      <div className="mx-auto max-w-2xl py-10 text-center">
        <div className="mx-auto mb-5 grid h-14 w-14 place-items-center rounded-lg bg-accent">
          <ScanFace className="h-6 w-6 text-accent-foreground" />
        </div>
        <h1 className="text-2xl font-normal">SkinGPT</h1>
        <p className="mx-auto mt-2 max-w-md text-ink-soft">
          Three guided views (front, left, right) produce image-based observations of oiliness, redness, pigmentation,
          texture, pores, fine lines and under-eye appearance — described as observations, never diagnoses.
        </p>
        <Link href="/scan/skin" className="mt-6 inline-block">
          <Button size="lg">Begin facial scan</Button>
        </Link>
      </div>
    );

  const byKind = Object.fromEntries(latest.observations.map((o) => [o.kind, o]));
  const concerns = [...latest.observations]
    .filter((o) => o.value_num !== null)
    .sort((a, b) => (b.value_num ?? 0) - (a.value_num ?? 0));
  const primary = concerns[0];
  const secondary = concerns[1];
  const referred = latest.safety_verdict?.verdict === "refer";

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-ink-soft">SkinGPT</p>
          <h1 className="mt-1 text-2xl font-normal">Skin Appearance Index</h1>
          <p className="metric-number mt-1">{latest.skin_appearance_index ?? "—"}</p>
          <p className="mt-1 text-sm text-ink-soft">
            A transparent composite of apparent attributes (0–100). Not a clinical score.
          </p>
        </div>
        <ConfidenceScale value={latest.overall_confidence} label="overall" className="w-40" />
      </header>

      {latest.safety_verdict && <SafetyBanner verdict={latest.safety_verdict} />}

      <div className="grid gap-4 sm:grid-cols-2">
        <Readout
          label="Primary concern"
          value={primary ? titleize(primary.kind) : "—"}
          caption={primary?.value_label ?? ""}
          confidence={primary?.confidence}
          flag={primary ? modelTrustLabel(primary)?.text : null}
        />
        <Readout
          label="Secondary concern"
          value={secondary ? titleize(secondary.kind) : "—"}
          caption={secondary?.value_label ?? ""}
          confidence={secondary?.confidence}
          flag={secondary ? modelTrustLabel(secondary)?.text : null}
        />
      </div>

      {/* Routines — only built when not referred; never recommends unnecessary products */}
      {!referred && (
        <div className="grid gap-4 md:grid-cols-2">
          <RoutineCard
            icon={Sun}
            title="Morning routine"
            steps={buildRoutine("morning", byKind, latest.recommendations)}
          />
          <RoutineCard
            icon={Moon}
            title="Night routine"
            steps={buildRoutine("night", byKind, latest.recommendations)}
          />
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Observations</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 sm:grid-cols-2">
            {latest.observations.map((o, i) => (
              <div key={i} className="flex items-start justify-between gap-3 rounded border p-3">
                <div className="min-w-0">
                  <p className="text-sm font-medium">{titleize(o.kind)}</p>
                  <p className="text-sm text-ink-soft">{o.value_label ?? o.value_num}</p>
                  <div className="mt-1.5 flex flex-wrap gap-1.5">
                    <Badge variant={o.observation_type === "visual_observation" ? "neutral" : "default"}>
                      {o.observation_type === "visual_observation" ? "visual observation" : "AI inference"}
                    </Badge>
                    {o.is_mock && <Badge variant="flag">mock</Badge>}
                  </div>
                </div>
                <ConfidenceChip value={o.confidence} />
              </div>
            ))}
          </div>
          <div className="mt-4">
            <WhyEvidence explain={latest.explanation ?? undefined} evidence={latest.explanation?.evidence} />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

/** Minimal, evidence-anchored routines. We deliberately do NOT pad the routine
 *  with unnecessary products — only cleanser, moisturizer, sunscreen, and an
 *  optional targeted active when an observation actually supports it. */
function buildRoutine(
  time: "morning" | "night",
  byKind: Record<string, any>,
  recs: Analysis["recommendations"]
) {
  const steps: { step: string; why: string; optional?: boolean }[] = [
    { step: "Gentle cleanser", why: "Baseline step for all skin types." },
    { step: "Moisturizer", why: "Supports barrier function; fragrance-free suits reactive skin." },
  ];
  if (time === "morning") {
    steps.push({ step: "Broad-spectrum SPF 30+ sunscreen", why: "Daily UV protection (AAD guidance)." });
  } else {
    const acne = (byKind["acne_like_lesion_count"]?.value_num ?? 0) > 6;
    const texture = (byKind["texture"]?.value_num ?? 0) > 0.22;
    if (acne || texture) {
      steps.push({
        step: "Optional targeted active (OTC)",
        why: "Only because an observation supports it. Introduce slowly, patch-test, and stop if irritated.",
        optional: true,
      });
    }
  }
  return steps;
}

function RoutineCard({
  icon: Icon,
  title,
  steps,
}: {
  icon: any;
  title: string;
  steps: { step: string; why: string; optional?: boolean }[];
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Icon className="h-4 w-4 text-accent" /> {title}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ol className="space-y-2.5">
          {steps.map((s, i) => (
            <li key={i} className="flex gap-3">
              <span className="mt-0.5 grid h-5 w-5 shrink-0 place-items-center rounded bg-accent text-[11px] font-semibold text-accent-foreground">
                {i + 1}
              </span>
              <div>
                <p className="text-sm font-medium">
                  {s.step} {s.optional && <Badge variant="neutral" className="ml-1">optional</Badge>}
                </p>
                <p className="text-xs text-ink-soft">{s.why}</p>
              </div>
            </li>
          ))}
        </ol>
      </CardContent>
    </Card>
  );
}
