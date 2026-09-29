"use client";

import * as React from "react";
import Link from "next/link";
import {
  Sparkles,
  Camera,
  Calendar,
  Activity,
  ArrowRight,
  ShieldCheck,
  FileText,
  Clock,
  CheckCircle2,
  AlertTriangle,
  TrendingUp,
  Layers,
  ChevronRight,
} from "lucide-react";
import { api, modelTrustLabel, type Analysis } from "@/lib/api";
import { AuthGate } from "@/components/auth-gate";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ConfidenceScale } from "@/components/confidence";
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

  if (loading) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center">
        <div className="flex items-center gap-3 text-ink-soft">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-accent border-t-transparent" />
          <p className="text-sm font-medium">Loading your hair profile…</p>
        </div>
      </div>
    );
  }

  if (!latest) return <FirstRun />;

  const lastScan = scans[0];
  const daysSince = lastScan
    ? Math.floor((Date.now() - new Date(lastScan.created_at).getTime()) / 86400000)
    : null;
  const nextIn = daysSince === null ? null : Math.max(0, SCAN_INTERVAL_DAYS - daysSince);
  const avgAdherence =
    adherence.length > 0 ? adherence.reduce((a, t) => a + t.adherence_pct, 0) / adherence.length : null;

  const hs = latest?.hair_summary ?? null;
  const trust = latest?.observations?.length ? modelTrustLabel(latest.observations[0]) : null;
  const verdict = latest?.safety_verdict?.verdict ?? "ok";

  return (
    <div className="space-y-8 animate-rise">
      {/* Welcome & Overview Header Card */}
      <div className="rounded-2xl border border-rule bg-gradient-to-br from-surface to-surface-sunken p-6 sm:p-8 shadow-xs">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="flex items-center gap-1.5 rounded-full bg-accent-wash px-3 py-1 text-xs font-semibold text-accent">
                <Sparkles className="h-3.5 w-3.5" />
                Latest Reading
              </span>
              {lastScan && (
                <span className="text-xs text-ink-faint">
                  Recorded on {new Date(lastScan.created_at).toLocaleDateString()}
                </span>
              )}
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-ink sm:text-3xl">
              {headline(latest.overall_confidence, hs)}
            </h1>
            <p className="mt-2 max-w-2xl text-sm leading-relaxed text-ink-soft">
              {latest.explanation?.summary ?? "Based on your most recent standardized 7-view capture."}
            </p>

            <div className="mt-4 flex flex-wrap items-center gap-2">
              <span
                className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold ${
                  verdict === "refer"
                    ? "bg-alert-wash text-alert"
                    : verdict === "caution"
                      ? "bg-caution-wash text-caution"
                      : "bg-ok-wash text-ok"
                }`}
              >
                {verdict === "ok" ? (
                  <CheckCircle2 className="h-3.5 w-3.5" />
                ) : (
                  <AlertTriangle className="h-3.5 w-3.5" />
                )}
                Safety Status: {verdict.toUpperCase()}
              </span>

              {trust && (
                <span className="rounded-full bg-surface-sunken border border-rule px-3 py-1 text-xs font-medium text-ink-faint">
                  {trust.text}
                </span>
              )}
            </div>
          </div>

          {/* Quick Action Buttons */}
          <div className="flex flex-wrap items-center gap-2.5">
            <Link href="/assessment">
              <Button size="lg" className="rounded-xl bg-accent text-white shadow-sm hover:bg-accent/90 gap-2">
                <Camera className="h-4 w-4" />
                <span>New Check</span>
              </Button>
            </Link>
            <Link href="/compare">
              <Button size="lg" variant="outline" className="rounded-xl gap-2">
                <Layers className="h-4 w-4" />
                <span>Compare</span>
              </Button>
            </Link>
            <Link href={`/report/${latest.session_id}`}>
              <Button size="lg" variant="outline" className="rounded-xl gap-2">
                <FileText className="h-4 w-4" />
                <span>Doctor Report</span>
              </Button>
            </Link>
          </div>
        </div>

        {/* Confidence scale widget */}
        <div className="mt-6 border-t border-rule pt-4">
          <ConfidenceScale
            value={latest.overall_confidence}
            label="Confidence calibration (based on capture sharpness & framing)"
          />
        </div>
      </div>

      {/* Key Metric KPI Cards */}
      <section>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-ink">Core Measurements</h2>
          <Link href="/timeline" className="text-xs font-semibold text-accent hover:underline flex items-center gap-1">
            <span>View Timeline</span>
            <ChevronRight className="h-3.5 w-3.5" />
          </Link>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {/* Hairline Card */}
          <MetricCard
            title="Hairline Position"
            value={hs?.hairline_position?.label ? "Localized" : "Baseline Set"}
            caption={hs?.hairline_position?.label ?? "Recession boundary detected"}
            confidence={hs?.hairline_position?.confidence}
            href="/timeline"
            icon={TrendingUp}
          />

          {/* Crown Card */}
          <MetricCard
            title="Crown Density"
            value={hs?.crown_density?.label?.replace("crown appears ", "") ?? "Moderate"}
            caption="Apparent density at top-back swirl"
            confidence={hs?.crown_density?.confidence}
            href="/timeline"
            icon={Activity}
          />

          {/* Scalp Visibility Card */}
          <MetricCard
            title="Scalp Visibility"
            value={pct(hs?.scalp_visibility?.value ?? null)}
            caption="Fraction of exposed scalp contrast"
            confidence={hs?.scalp_visibility?.confidence}
            href="/timeline"
            icon={CheckCircle2}
          />
        </div>
      </section>

      {/* Regimen & Schedule Tracker */}
      <section>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-ink">Regimen & Progress</h2>
          <Link href="/treatments" className="text-xs font-semibold text-accent hover:underline flex items-center gap-1">
            <span>Manage Treatments</span>
            <ChevronRight className="h-3.5 w-3.5" />
          </Link>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {/* Adherence Card */}
          <MetricCard
            title="Treatment Adherence"
            value={avgAdherence === null ? "—" : `${avgAdherence.toFixed(0)}%`}
            caption={
              adherence.length
                ? `${adherence.length} active treatment${adherence.length === 1 ? "" : "s"} tracked`
                : "No treatments recorded yet"
            }
            href="/treatments"
            icon={Clock}
          />

          {/* Shedding Trend */}
          <MetricCard
            title="Shedding Trend"
            value={sheddingValue(shedding)}
            caption={shedding?.trend_note ?? "Log shedding count to compute trend"}
            href="/shedding"
            icon={Activity}
          />

          {/* Next Scan Due */}
          <MetricCard
            title="Next Check Due"
            value={nextIn === null ? "—" : nextIn === 0 ? "Ready" : `${nextIn} days`}
            caption={`${SCAN_INTERVAL_DAYS}-day interval ensures comparable hair cycles`}
            href="/assessment"
            icon={Calendar}
          />
        </div>
      </section>

      {/* Clinical Evidence & Rationale Card */}
      <Card className="rounded-2xl border border-rule overflow-hidden shadow-xs">
        <CardContent className="p-6 sm:p-8">
          <div className="flex items-center gap-2 mb-4">
            <ShieldCheck className="h-5 w-5 text-accent" />
            <h3 className="text-base font-bold text-ink">Clinical Evidence & Method Transparency</h3>
          </div>
          <WhyEvidence explain={latest.explanation ?? undefined} evidence={latest.explanation?.evidence} />
        </CardContent>
      </Card>
    </div>
  );
}

function MetricCard({
  title,
  value,
  caption,
  confidence,
  href,
  icon: Icon,
}: {
  title: string;
  value: string;
  caption: string;
  confidence?: number | null;
  href: string;
  icon: any;
}) {
  return (
    <Link
      href={href}
      className="group flex flex-col justify-between rounded-2xl border border-rule bg-surface p-5 shadow-xs transition-all hover:border-accent-edge hover:shadow-md hover:-translate-y-0.5"
    >
      <div>
        <div className="flex items-center justify-between gap-2">
          <span className="text-xs font-semibold uppercase tracking-wider text-ink-faint">{title}</span>
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-surface-sunken text-ink-faint group-hover:bg-accent-wash group-hover:text-accent transition-colors">
            <Icon className="h-4 w-4" />
          </div>
        </div>
        <p className="mt-2 text-2xl font-bold tracking-tight text-ink group-hover:text-accent transition-colors">
          {value}
        </p>
        <p className="mt-1 text-xs text-ink-soft leading-relaxed">{caption}</p>
      </div>

      {confidence != null && (
        <div className="mt-4 flex items-center justify-between border-t border-rule pt-3 text-[11px] text-ink-faint">
          <span>Accuracy Confidence</span>
          <span className="font-semibold text-ink">{(confidence * 100).toFixed(0)}%</span>
        </div>
      )}
    </Link>
  );
}

function headline(confidence: number, hs: any) {
  if (confidence < 0.4) return "Baseline Recording in Progress";
  const label = hs?.apparent_density?.label ?? hs?.crown_density?.label;
  if (!label) return "Baseline Recorded";
  return `Apparent Density: ${String(label).replace(/^apparent |^crown appears /, "")}`;
}

function sheddingValue(trend: any) {
  if (!trend || trend.trend === "insufficient_data") return "Stable / Untracked";
  return { increasing: "Rising", decreasing: "Decreasing", stable: "Steady" }[trend.trend as string] ?? "Stable";
}

function FirstRun() {
  return (
    <div className="mx-auto max-w-3xl py-6 animate-rise">
      <div className="rounded-3xl border border-rule bg-gradient-to-br from-surface via-surface to-surface-sunken p-8 sm:p-12 shadow-sm text-center">
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-tr from-accent to-blue-400 text-white shadow-md shadow-accent/25">
          <Sparkles className="h-7 w-7" />
        </div>

        <h1 className="mt-6 text-3xl font-bold tracking-tight text-ink sm:text-4xl">
          Welcome to HairGPT
        </h1>
        <p className="mx-auto mt-3 max-w-xl text-base text-ink-soft leading-relaxed">
          Get a comprehensive, clinical-grade baseline analysis of your hair and scalp. Track density changes over time with transparent AI confidence scores.
        </p>

        <div className="mt-8 grid gap-4 text-left sm:grid-cols-2">
          {[
            {
              step: "01",
              title: "About You & Your Story",
              desc: "Quick questions regarding when and where hair thinning was first noticed.",
            },
            {
              step: "02",
              title: "Health & Habit Factors",
              desc: "Assess medical, stress, and styling variables that photos alone cannot see.",
            },
            {
              step: "03",
              title: "Clinical Safety Screen",
              desc: "Automated heuristic checks to detect signs requiring a physician.",
            },
            {
              step: "04",
              title: "Guided 7-Angle Scan",
              desc: "On-screen guides calibrate contrast and sharpness for longitudinal tracking.",
            },
          ].map((item) => (
            <div
              key={item.step}
              className="flex items-start gap-3.5 rounded-2xl border border-rule bg-surface p-4 shadow-xs"
            >
              <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-accent-wash text-xs font-bold text-accent">
                {item.step}
              </span>
              <div>
                <p className="text-sm font-semibold text-ink">{item.title}</p>
                <p className="mt-1 text-xs text-ink-soft leading-snug">{item.desc}</p>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-10 flex flex-wrap items-center justify-center gap-3">
          <Link href="/assessment">
            <Button size="lg" className="rounded-xl bg-accent px-8 py-3 text-white shadow-md shadow-accent/25 hover:bg-accent/90 gap-2">
              <span>Start Free Assessment</span>
              <ArrowRight className="h-4 w-4" />
            </Button>
          </Link>
          <Link href="/scan/hair">
            <Button size="lg" variant="outline" className="rounded-xl px-6 py-3 gap-2">
              <Camera className="h-4 w-4" />
              <span>Just Take a Scan</span>
            </Button>
          </Link>
        </div>
      </div>
    </div>
  );
}
