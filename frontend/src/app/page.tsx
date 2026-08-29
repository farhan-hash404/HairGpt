"use client";

import * as React from "react";
import Link from "next/link";
import { api, modelTrustLabel, type Analysis } from "@/lib/api";
import { AuthGate } from "@/components/auth-gate";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ConfidenceScale } from "@/components/confidence";
import { Readout } from "@/components/metric-card";
import { WhyEvidence } from "@/components/why-evidence";
import { pct } from "@/lib/utils";

const SCAN_INTERVAL_DAYS = 30;

export default function OverviewPage() {
  return (
    <AuthGate>
      <Overview />
    </AuthGate>
  );
}

function Overview() {
  const [latest, setLatest] = React.useState<Analysis | null>(null);
  const [scans, setScans] = React.useState<any[]>([]);
  const [adherence, setAdherence] = React.useState<any[]>([]);
  const [shedding, setShedding] = React.useState<any>(null);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    (async () => {
      try {
        const list = await api.listScans();
        setScans(list);
        const complete = list.find((s: any) => s.status === "complete");
        if (complete) setLatest(await api.result(complete.id));
        setAdherence(await api.adherenceSummary());
        setShedding(await api.sheddingTrend(60));
      } catch {
        /* first run */
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  if (loading) return <p className="text-sm text-ink-soft">Loading…</p>;
  if (!latest) return <FirstRun />;

  const lastScan = scans[0];
  const daysSince = lastScan
    ? Math.floor((Date.now() - new Date(lastScan.created_at).getTime()) / 86400000)
    : null;
  const nextIn = daysSince === null ? null : Math.max(0, SCAN_INTERVAL_DAYS - daysSince);
  const avgAdherence =
    adherence.length > 0 ? adherence.reduce((a, t) => a + t.adherence_pct, 0) / adherence.length : null;

  const hs = latest.hair_summary ?? null;
  const trust = latest.observations.length
    ? modelTrustLabel(latest.observations[0])
    : null;
  const verdict = latest.safety_verdict?.verdict ?? "ok";

  return (
    <div className="space-y-8">
      {/* Record header. The thesis of the page: a reading, with its confidence
          and its caveats attached, not a verdict. */}
      <header className="animate-rise">
        <div className="flex flex-wrap items-end justify-between gap-x-8 gap-y-4">
          <div className="min-w-0">
            <p className="label">Hair &amp; scalp · latest reading</p>
            <h1 className="mt-2 max-w-[18ch] text-3xl font-normal">
              {headline(latest.overall_confidence, hs)}
            </h1>
            <p className="mt-2 max-w-[62ch] text-sm text-ink-soft">
              {latest.explanation?.summary ?? "Based on your most recent scan."}
            </p>
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <Badge variant={verdict === "refer" ? "alert" : verdict === "caution" ? "caution" : "ok"}>
                safety: {verdict}
              </Badge>
              {trust && <Badge variant="flag">{trust.text}</Badge>}
              {lastScan && (
                <span className="readout text-2xs text-ink-faint">
                  {new Date(lastScan.created_at).toLocaleDateString()}
                </span>
              )}
            </div>
          </div>

          <ConfidenceScale
            value={latest.overall_confidence}
            label="overall interpretation"
            className="w-full max-w-[220px]"
          />
        </div>

        <div className="scale-rule mt-6" aria-hidden="true" />
      </header>

      {/* Measurements */}
      <section>
        <h2 className="label mb-3">Measurements</h2>
        <div className="grid gap-px overflow-hidden rounded-lg border bg-rule sm:grid-cols-2 lg:grid-cols-3">
          <div className="bg-surface">
            <Readout
              label="Hairline"
              value={hs?.hairline_position?.label ? "Localized" : "—"}
              caption={hs?.hairline_position?.label ?? "No hairline reading in the last scan"}
              confidence={hs?.hairline_position?.confidence ?? null}
              href="/timeline"
            />
          </div>
          <div className="bg-surface">
            <Readout
              label="Crown"
              value={hs?.crown_density?.label?.replace("crown appears ", "") ?? "—"}
              caption="Apparent crown density"
              confidence={hs?.crown_density?.confidence ?? null}
              href="/timeline"
            />
          </div>
          <div className="bg-surface">
            <Readout
              label="Scalp visibility"
              value={pct(hs?.scalp_visibility?.value ?? null)}
              caption="Apparent fraction of visible scalp"
              confidence={hs?.scalp_visibility?.confidence ?? null}
              href="/timeline"
            />
          </div>
        </div>
      </section>

      {/* Programme — the things the user controls, distinct from what we measured. */}
      <section>
        <h2 className="label mb-3">Your programme</h2>
        <div className="grid gap-px overflow-hidden rounded-lg border bg-rule sm:grid-cols-2 lg:grid-cols-3">
          <div className="bg-surface">
            <Readout
              label="Treatment adherence"
              value={avgAdherence === null ? "—" : avgAdherence.toFixed(0)}
              unit={avgAdherence === null ? undefined : "%"}
              caption={
                adherence.length
                  ? `${adherence.length} active treatment${adherence.length === 1 ? "" : "s"}`
                  : "Nothing tracked yet"
              }
              href="/treatments"
            />
          </div>
          <div className="bg-surface">
            <Readout
              label="Shedding"
              value={sheddingValue(shedding)}
              caption={shedding?.trend_note ?? "Log a few days to see a trend"}
              href="/shedding"
            />
          </div>
          <div className="bg-surface">
            <Readout
              label="Next scan"
              value={nextIn === null ? "—" : nextIn === 0 ? "Due" : `${nextIn}d`}
              caption={`Even ${SCAN_INTERVAL_DAYS}-day spacing keeps scans comparable`}
            />
          </div>
        </div>
      </section>

      <section className="flex flex-wrap items-center gap-2">
        <Link href="/assessment">
          <Button size="lg">New assessment</Button>
        </Link>
        <Link href="/compare">
          <Button size="lg" variant="outline">
            Compare scans
          </Button>
        </Link>
        <Link href={`/report/${latest.session_id}`}>
          <Button size="lg" variant="outline">
            Doctor report
          </Button>
        </Link>
      </section>

      <Card>
        <CardContent className="pt-5">
          <WhyEvidence explain={latest.explanation ?? undefined} evidence={latest.explanation?.evidence} />
        </CardContent>
      </Card>

      {!!latest.disclaimers?.length && (
        <section>
          <h2 className="label mb-2">Standing limitations</h2>
          <ul className="space-y-1 text-xs text-ink-faint">
            {latest.disclaimers.map((d, i) => (
              <li key={i} className="flex gap-2">
                <span aria-hidden="true">—</span>
                <span>{d}</span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}

function headline(confidence: number, hs: any) {
  if (confidence < 0.4) return "Not enough signal yet";
  const label = hs?.apparent_density?.label ?? hs?.crown_density?.label;
  if (!label) return "Baseline recorded";
  return `Apparent density reads ${String(label).replace(/^apparent |^crown appears /, "")}`;
}

function sheddingValue(trend: any) {
  if (!trend || trend.trend === "insufficient_data") return "—";
  return { increasing: "Rising", decreasing: "Falling", stable: "Steady" }[trend.trend as string] ?? "—";
}

function FirstRun() {
  return (
    <div className="mx-auto max-w-2xl animate-rise py-8">
      <p className="label">Getting started</p>
      <h1 className="mt-3 text-4xl font-normal">
        A measured reading of your hair, <em className="font-normal italic">with its uncertainty attached</em>.
      </h1>
      <p className="mt-4 max-w-[62ch] text-base text-ink-soft">
        The assessment asks about your history first — the things a photo cannot show — then walks you through seven
        standardized views. Every number it returns carries a confidence, and it will tell you plainly when a change
        is too small to be real.
      </p>

      <ol className="mt-8 divide-y border-y">
        {[
          ["Your history", "Onset, pattern, conditions, medications. This is what a clinician asks first."],
          ["Safety check", "A handful of signs a camera cannot see. Any one of them routes you to a clinician."],
          ["Seven views", "Guided capture with quality gating, so nothing unusable is ever analysed."],
          ["The reading", "Observations, confidence, cited evidence, and what it cannot tell you."],
        ].map(([title, body], i) => (
          <li key={title} className="flex gap-4 py-4">
            <span className="readout mt-0.5 text-sm text-ink-faint">{String(i + 1).padStart(2, "0")}</span>
            <div>
              <p className="font-medium">{title}</p>
              <p className="mt-0.5 text-sm text-ink-soft">{body}</p>
            </div>
          </li>
        ))}
      </ol>

      <div className="mt-8 flex flex-wrap gap-2">
        <Link href="/assessment">
          <Button size="lg">Begin assessment</Button>
        </Link>
        <Link href="/scan/hair">
          <Button size="lg" variant="outline">
            Just take a scan
          </Button>
        </Link>
      </div>
    </div>
  );
}
