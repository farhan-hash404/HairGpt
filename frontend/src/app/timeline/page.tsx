"use client";

import * as React from "react";
import Link from "next/link";
import {
  Sparkles,
  TrendingUp,
  Activity,
  CheckCircle2,
  Calendar,
  Pill,
  Clock,
  ArrowRight,
  Info,
  ChevronRight,
  ShieldCheck,
  Eye,
  Layers,
} from "lucide-react";
import { api } from "@/lib/api";
import { AuthGate } from "@/components/auth-gate";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { titleize } from "@/lib/utils";

type Point = {
  date: string;
  value: number | null;
  label: string | null;
  confidence: number;
  is_mock: boolean;
};

export default function TimelinePage() {
  return (
    <AuthGate>
      <Timeline />
    </AuthGate>
  );
}

function Timeline() {
  const [data, setData] = React.useState<any>(null);
  const [adherence, setAdherence] = React.useState<any[]>([]);

  React.useEffect(() => {
    api.timeline().then(setData).catch(() => setData({ series: {}, treatments: [], scan_history: [] }));
    api.adherenceSummary().then(setAdherence).catch(() => setAdherence([]));
  }, []);

  if (!data) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center">
        <div className="flex items-center gap-3 text-ink-soft">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-accent border-t-transparent" />
          <p className="text-sm font-medium">Loading your hair progress timeline…</p>
        </div>
      </div>
    );
  }

  const series: Record<string, Point[]> = data.series ?? {};
  const hasAny = Object.values(series).some((s) => s.length > 0);

  return (
    <div className="mx-auto max-w-5xl space-y-8 animate-rise">
      {/* Page Title & Intro */}
      <div>
        <div className="flex items-center gap-2 mb-2">
          <span className="flex items-center gap-1.5 rounded-full bg-accent-wash px-3 py-1 text-xs font-semibold text-accent">
            <TrendingUp className="h-3.5 w-3.5" />
            Longitudinal Progress
          </span>
          <span className="text-xs text-ink-faint">Across all standardized scans</span>
        </div>
        <h1 className="text-2xl font-bold tracking-tight text-ink sm:text-3xl">
          Your Hair Progress & Timeline
        </h1>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-ink-soft">
          Track how your hair density, crown coverage, and hairline stability change over time.
          All observations are automatically translated from raw sensor metrics into plain-English percentages.
        </p>

        {/* Helpful Explanation Alert */}
        <div className="mt-4 flex items-start gap-3 rounded-2xl border border-blue-100 bg-blue-50/70 dark:border-blue-900/40 dark:bg-blue-950/20 p-4 text-xs leading-relaxed text-blue-900 dark:text-blue-200">
          <Info className="h-4 w-4 shrink-0 mt-0.5 text-accent" />
          <div>
            <span className="font-semibold">How to read your numbers:</span> Small day-to-day variations (under 3%) are normal and caused by hair parting, wetness, or room lighting. Meaningful trends appear when reviewing scans taken 30 to 60 days apart.
          </div>
        </div>
      </div>

      {/* Progress Sparkline Cards */}
      {!hasAny ? (
        <Card className="rounded-2xl border border-rule p-8 text-center shadow-xs">
          <CardContent className="space-y-4">
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-surface-sunken text-ink-faint">
              <Calendar className="h-6 w-6" />
            </div>
            <div>
              <p className="text-base font-semibold text-ink">No completed scans recorded yet</p>
              <p className="mt-1 text-xs text-ink-soft max-w-md mx-auto">
                Complete your first standardized 7-view scan to record your baseline reading.
              </p>
            </div>
            <Link href="/assessment">
              <Button size="lg" className="rounded-xl bg-accent text-white hover:bg-accent/90">
                Start Your First Check
              </Button>
            </Link>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-5">
          {Object.entries(series).map(([kind, points]) =>
            points.length ? <FriendlyMetricSparkline key={kind} kind={kind} points={points} /> : null
          )}
        </div>
      )}

      {/* Treatment Timeline Lane */}
      <Card className="rounded-2xl border border-rule shadow-xs overflow-hidden">
        <CardHeader className="border-b border-rule bg-surface p-5 sm:p-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-accent-wash text-accent">
                <Pill className="h-4 w-4" />
              </div>
              <div>
                <CardTitle className="text-base font-bold text-ink">Active Regimen & Daily Treatments</CardTitle>
                <p className="text-xs text-ink-faint mt-0.5">Track consistency to correlate with density changes</p>
              </div>
            </div>
            <Link href="/treatments">
              <Button variant="outline" size="sm" className="rounded-lg text-xs gap-1.5">
                <span>Manage Regimen</span>
                <ChevronRight className="h-3 w-3" />
              </Button>
            </Link>
          </div>
        </CardHeader>

        <CardContent className="p-5 sm:p-6">
          {data.treatments?.length ? (
            <div className="grid gap-3 sm:grid-cols-2">
              {data.treatments.map((t: any) => {
                const a = adherence.find((x) => x.treatment_id === t.id);
                const adherencePct = a ? a.adherence_pct : 100;

                return (
                  <div
                    key={t.id}
                    className="flex flex-col justify-between rounded-xl border border-rule bg-surface p-4 shadow-2xs"
                  >
                    <div>
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-sm font-semibold text-ink">{t.name}</span>
                        <span className="rounded-full bg-ok-wash px-2 py-0.5 text-[11px] font-semibold text-ok">
                          {adherencePct}% consistency
                        </span>
                      </div>
                      <p className="mt-1 text-xs text-ink-soft">
                        {t.category === "topical" ? "🧴 Topical Application" : "💊 Oral Medication"} • Started {new Date(t.start_date).toLocaleDateString()}
                      </p>
                    </div>

                    <div className="mt-3">
                      <div className="flex items-center justify-between text-[11px] text-ink-faint mb-1">
                        <span>Adherence Goal</span>
                        <span className="font-semibold text-ink">{adherencePct}%</span>
                      </div>
                      <div className="h-1.5 w-full overflow-hidden rounded-full bg-rule">
                        <div
                          className="h-full rounded-full bg-ok transition-all"
                          style={{ width: `${adherencePct}%` }}
                        />
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="text-center py-6 text-ink-soft">
              <p className="text-xs">No active treatments logged yet.</p>
              <Link href="/treatments" className="mt-2 inline-block text-xs font-semibold text-accent hover:underline">
                + Add your daily vitamins or treatments
              </Link>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Scan History */}
      <Card className="rounded-2xl border border-rule shadow-xs overflow-hidden">
        <CardHeader className="border-b border-rule bg-surface p-5 sm:p-6">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-surface-sunken text-ink-faint">
              <Calendar className="h-4 w-4" />
            </div>
            <div>
              <CardTitle className="text-base font-bold text-ink">Recorded Scan History</CardTitle>
              <p className="text-xs text-ink-faint mt-0.5">Click any scan to inspect individual image angles and safety reports</p>
            </div>
          </div>
        </CardHeader>

        <CardContent className="p-0">
          <div className="divide-y border-rule">
            {(data.scan_history ?? []).map((s: any) => (
              <Link
                key={s.session_id}
                href={`/scan/${s.session_id}/result`}
                className="flex items-center justify-between p-4 sm:px-6 hover:bg-surface-sunken transition-colors group"
              >
                <div className="flex items-center gap-3">
                  <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-accent-wash text-accent font-semibold text-xs">
                    {new Date(s.date).getDate()}
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-ink group-hover:text-accent transition-colors">
                      {new Date(s.date).toLocaleDateString(undefined, {
                        month: "short",
                        day: "numeric",
                        year: "numeric",
                      })}{" "}
                      • 7-Angle Hair Scan
                    </p>
                    <p className="text-xs text-ink-faint mt-0.5">Standardized capture with quality gating</p>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  {s.overall_confidence !== null && (
                    <span className="hidden sm:inline-flex items-center gap-1 rounded-full bg-surface-sunken border border-rule px-2.5 py-0.5 text-xs text-ink-soft">
                      <ShieldCheck className="h-3 w-3 text-accent" />
                      {Math.round(s.overall_confidence * 100)}% Confidence
                    </span>
                  )}
                  <ChevronRight className="h-4 w-4 text-ink-faint group-hover:text-accent group-hover:translate-x-0.5 transition-all" />
                </div>
              </Link>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

/** Meta information translating clinical metric keys into friendly explanations */
const METRIC_INFO: Record<
  string,
  { title: string; subtitle: string; icon: any; isPercentage: boolean; invertQuality?: boolean; unit: string }
> = {
  scalp_visibility: {
    title: "Scalp Visibility",
    subtitle: "How much scalp is showing through your hair. Lower is fuller.",
    icon: Eye,
    isPercentage: true,
    invertQuality: true, // Lower is better!
    unit: "%",
  },
  apparent_density: {
    title: "Overall Hair Density",
    subtitle: "Concentration and volume of strands across your head.",
    icon: Activity,
    isPercentage: true,
    unit: "%",
  },
  crown_density: {
    title: "Crown & Swirl Density",
    subtitle: "Apparent fullness at the top-back swirl area.",
    icon: TrendingUp,
    isPercentage: true,
    unit: "%",
  },
  hairline_position: {
    title: "Hairline Stability",
    subtitle: "Tracks temple and frontal borders for recession signs.",
    icon: CheckCircle2,
    isPercentage: false,
    unit: "cm",
  },
};

/**
 * Friendly Sparkline Component
 * Converts obscure floating points (like 0.296) into clear percentages (like 29.6%),
 * and adds friendly trend summaries ("Steady & Stable", "Improving", etc.).
 */
function FriendlyMetricSparkline({ kind, points }: { kind: string; points: Point[] }) {
  const meta = METRIC_INFO[kind] || {
    title: titleize(kind),
    subtitle: "Longitudinal tracking observation across your scans.",
    icon: Activity,
    isPercentage: false,
    unit: "",
  };

  const Icon = meta.icon;

  // Format values into friendly numbers
  const formatVal = (v: number | null) => {
    if (v === null) return "—";
    if (meta.isPercentage) {
      return `${(v * 100).toFixed(1)}%`;
    }
    if (kind === "hairline_position") {
      return "Stable";
    }
    return v.toFixed(2);
  };

  const rawVals = points.map((p) => p.value ?? 0);
  const dataMin = Math.min(...rawVals);
  const dataMax = Math.max(...rawVals);
  const span = dataMax - dataMin;
  const padDomain = span > 0 ? span * 0.35 : 0.03;
  const min = dataMin - padDomain;
  const max = dataMax + padDomain;

  const w = 540;
  const h = 80;
  const pad = 12;
  const x = (i: number) => (points.length === 1 ? w / 2 : pad + (i * (w - pad * 2)) / (points.length - 1));
  const y = (v: number) => h - pad - ((v - min) / (max - min || 1)) * (h - pad * 2);

  const path = points.map((p, i) => `${i === 0 ? "M" : "L"} ${x(i)} ${y(p.value ?? 0)}`).join(" ");
  const first = points[0];
  const last = points[points.length - 1];
  const delta = (last.value ?? 0) - (first.value ?? 0);

  // Friendly trend interpretation
  const absDeltaPct = meta.isPercentage ? Math.abs(delta * 100) : Math.abs(delta);
  const isMeaningful = absDeltaPct > 2.5; // Under 2.5% is normal lighting variation

  let trendBadge = "🟢 Steady & Stable";
  let trendExplanation = `Readings have remained steady within a normal ±${absDeltaPct.toFixed(1)}% range across your last ${points.length} scans.`;

  if (isMeaningful) {
    if (meta.invertQuality) {
      // For scalp visibility, negative delta means LESS scalp is showing = IMPROVEMENT!
      if (delta < 0) {
        trendBadge = "🟢 Improving Coverage";
        trendExplanation = `Visible scalp decreased by ${absDeltaPct.toFixed(1)}%, indicating fuller hair coverage!`;
      } else {
        trendBadge = "🟡 Slight Increase in Visibility";
        trendExplanation = `Visible scalp increased by ${absDeltaPct.toFixed(1)}%. Ensure consistent lighting on your next check.`;
      }
    } else {
      if (delta > 0) {
        trendBadge = "🟢 Improving Density";
        trendExplanation = `Density increased by ${absDeltaPct.toFixed(1)}% across your recent scans.`;
      } else {
        trendBadge = "🟡 Slight Decrease";
        trendExplanation = `Density decreased by ${absDeltaPct.toFixed(1)}%. Recommend tracking again in 30 days.`;
      }
    }
  }

  return (
    <Card className="rounded-2xl border border-rule bg-surface p-5 sm:p-6 shadow-xs">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-accent-wash text-accent">
            <Icon className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-base font-bold text-ink">{meta.title}</h3>
              <span className="rounded-full bg-surface-sunken border border-rule px-2.5 py-0.5 text-[11px] font-medium text-ink-soft">
                {trendBadge}
              </span>
            </div>
            <p className="mt-0.5 text-xs text-ink-soft">{meta.subtitle}</p>
          </div>
        </div>

        {/* Current Reading Hero Value */}
        <div className="text-right">
          <p className="text-xs font-semibold uppercase tracking-wider text-ink-faint">Latest Reading</p>
          <p className="text-xl font-bold text-accent">
            {formatVal(last.value)}
          </p>
          <p className="text-[11px] text-ink-faint">
            {(last.confidence * 100).toFixed(0)}% Accuracy Confidence
          </p>
        </div>
      </div>

      {/* Visual Chart Area */}
      <div className="mt-5 rounded-xl border border-rule/70 bg-surface-sunken/40 p-4">
        <div className="flex items-center justify-between text-[11px] font-medium text-ink-faint mb-2">
          <span>Scan Timeline</span>
          <span>
            Range: {formatVal(min)} to {formatVal(max)}
          </span>
        </div>

        <div className="relative">
          <svg viewBox={`0 0 ${w} ${h}`} className="h-20 w-full overflow-visible" role="img">
            {/* Background grid line */}
            <line x1="0" y1={h / 2} x2={w} y2={h / 2} stroke="currentColor" className="text-rule stroke-[1] stroke-dasharray-[3_3]" />

            {/* Main Sparkline Path */}
            <path
              d={path}
              fill="none"
              stroke="hsl(var(--accent))"
              strokeWidth={2.5}
              strokeLinecap="round"
              strokeLinejoin="round"
            />

            {/* Individual Data Points */}
            {points.map((p, i) => (
              <g key={i}>
                <circle
                  cx={x(i)}
                  cy={y(p.value ?? 0)}
                  r={5}
                  className="fill-accent stroke-surface stroke-[2]"
                />
              </g>
            ))}
          </svg>

          {/* Dates underneath points */}
          <div className="flex items-center justify-between text-[10px] text-ink-faint mt-2">
            {points.map((p, i) => (
              <span key={i} className="tabular-nums">
                {new Date(p.date).toLocaleDateString(undefined, { month: "short", day: "numeric" })}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Friendly Takeaway */}
      <div className="mt-3 flex items-center justify-between text-xs text-ink-soft border-t border-rule pt-3">
        <span className="leading-relaxed">{trendExplanation}</span>
      </div>
    </Card>
  );
}
