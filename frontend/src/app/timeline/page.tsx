"use client";

import * as React from "react";
import Link from "next/link";
import { ArrowUpRight, ChevronRight } from "lucide-react";
import { api } from "@/lib/api";
import { AuthGate } from "@/components/auth-gate";
import { buttonVariants } from "@/components/ui/button";
import { ConfidenceChip } from "@/components/confidence";
import { MetricTerm } from "@/components/metric-term";
import { PageHeader } from "@/components/page-header";
import { Readout } from "@/components/readout";
import { ReticleMark } from "@/components/wordmark";
import { titleize } from "@/lib/utils";

type Point = {
  date: string;
  value: number | null;
  label: string | null;
  confidence: number;
  is_mock: boolean;
};

/* Day-to-day differences below this many points are usually lighting, parting
   or wet hair, not change. */
const NOISE_POINTS = 2.5;

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
      <div className="flex min-h-[40vh] items-center justify-center gap-3 text-ink-soft">
        <ReticleMark className="h-6 w-6 animate-spin text-ink [animation-duration:2.4s]" />
        <p className="label">Loading your timeline…</p>
      </div>
    );
  }

  const series: Record<string, Point[]> = data.series ?? {};
  const entries = Object.entries(series).filter(([, points]) => points.length > 0);

  return (
    <div className="mx-auto max-w-5xl animate-rise">
      <PageHeader
        index="Nº 04"
        eyebrow="Timeline · every standardised scan"
        title={
          <>
            How the readings have <span className="marker">moved</span>.
          </>
        }
        dek="Scans 30 to 60 days apart show real change. Differences under three points are usually light, parting or damp hair."
      />

      {entries.length === 0 ? (
        <div className="crop-marks mx-auto max-w-xl">
          <div className="graph-paper border border-rule bg-surface px-6 py-12 text-center">
            <ReticleMark className="mx-auto h-12 w-12 text-ink-faint" />
            <p className="mt-4 font-display text-2xl">No completed scans yet.</p>
            <p className="mx-auto mt-2 max-w-sm text-sm text-ink-soft">
              Your first standardised capture becomes the baseline every later one is measured against.
            </p>
            <Link href="/assessment" className={buttonVariants({ className: "mt-6" })}>
              Start your first check
            </Link>
          </div>
        </div>
      ) : (
        <div className="space-y-12">
          {entries.map(([kind, points], i) => (
            <MetricFigure key={kind} index={i + 1} kind={kind} points={points} />
          ))}
        </div>
      )}

      <section className="mt-16">
        <div className="mb-4 flex items-end justify-between gap-4">
          <h2 className="flex items-baseline gap-3 text-2xl">
            <span className="readout text-sm text-ink-faint">A.</span>
            Regimen alongside
          </h2>
          <Link href="/treatments" className="group inline-flex items-center gap-1 text-sm text-ink-soft hover:text-ink">
            Manage treatments
            <ArrowUpRight className="h-3.5 w-3.5 transition-transform group-hover:-translate-y-0.5 group-hover:translate-x-0.5" />
          </Link>
        </div>
        {data.treatments?.length ? (
          <ul className="border-t border-ink">
            {data.treatments.map((t: any) => {
              const a = adherence.find((x) => x.treatment_id === t.id);
              const pct: number | null = a ? a.adherence_pct : null;
              return (
                <li key={t.id} className="grid items-center gap-x-6 gap-y-2 border-b border-rule py-4 sm:grid-cols-[1fr_12rem_7rem]">
                  <div>
                    <p className="text-[0.95rem] font-medium">{t.name}</p>
                    <p className="caption mt-0.5">
                      {t.category === "topical" ? "Topical" : titleize(t.category ?? "treatment")} · started{" "}
                      {new Date(t.start_date).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" })}
                    </p>
                  </div>
                  <div className="h-1.5 w-full bg-surface-sunken" aria-hidden="true">
                    <div className="h-full bg-ink" style={{ width: `${pct ?? 0}%` }} />
                  </div>
                  <p className="text-right text-sm">
                    {pct === null ? (
                      <span className="text-ink-faint">no logs</span>
                    ) : (
                      <>
                        <Readout value={pct} suffix="%" className="text-base" />
                        <span className="caption block">last 30 days</span>
                      </>
                    )}
                  </p>
                </li>
              );
            })}
          </ul>
        ) : (
          <p className="border-y border-rule py-6 text-sm text-ink-soft">
            No treatments logged yet.{" "}
            <Link href="/treatments" className="text-accent underline decoration-accent/40 underline-offset-4 hover:decoration-accent">
              Add what you use
            </Link>{" "}
            to see it beside your readings.
          </p>
        )}
      </section>

      <section className="mt-16">
        <h2 className="mb-4 flex items-baseline gap-3 text-2xl">
          <span className="readout text-sm text-ink-faint">B.</span>
          Scan register
        </h2>
        <ul className="border-t border-ink">
          {(data.scan_history ?? []).map((s: any, i: number) => (
            <li key={s.session_id}>
              <Link
                href={`/scan/${s.session_id}/result`}
                className="group grid grid-cols-[2.5rem_1fr_auto] items-center gap-4 border-b border-rule py-3.5 transition-colors hover:bg-surface-sunken/70 sm:grid-cols-[2.5rem_11rem_1fr_auto]"
              >
                <span className="readout text-xs text-ink-faint">
                  {String((data.scan_history?.length ?? 0) - i).padStart(2, "0")}
                </span>
                <span className="readout text-sm">
                  {new Date(s.date).toLocaleDateString(undefined, { day: "2-digit", month: "short", year: "numeric" })}
                </span>
                <span className="hidden text-sm text-ink-soft sm:block">Standardised capture · quality-gated</span>
                <span className="flex items-center gap-3">
                  {s.overall_confidence !== null && s.overall_confidence !== undefined && (
                    <ConfidenceChip value={s.overall_confidence} />
                  )}
                  <ChevronRight className="h-4 w-4 text-ink-faint transition-transform group-hover:translate-x-0.5 group-hover:text-ink" />
                </span>
              </Link>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

const METRIC_INFO: Record<string, { title: string; subtitle: string; percent: boolean; lowerIsFuller?: boolean }> = {
  scalp_visibility: {
    title: "Scalp visibility",
    subtitle: "How much scalp shows through. Lower means fuller coverage.",
    percent: true,
    lowerIsFuller: true,
  },
  apparent_density: {
    title: "Apparent density",
    subtitle: "Coverage of strands across the whole scalp.",
    percent: true,
  },
  crown_density: {
    title: "Crown density",
    subtitle: "Apparent fullness at the crown swirl.",
    percent: true,
  },
  hairline_position: {
    title: "Hairline",
    subtitle: "Where the frontal border sits in the standard view.",
    percent: false,
  },
};

/** One metric, drawn as an instrument trace on graph paper. */
function MetricFigure({ index, kind, points }: { index: number; kind: string; points: Point[] }) {
  const meta = METRIC_INFO[kind] ?? { title: titleize(kind), subtitle: "Tracked across your scans.", percent: false };
  const numeric = points.filter((p) => p.value !== null);
  const first = numeric[0];
  const last = numeric[numeric.length - 1] ?? points[points.length - 1];

  const scale = meta.percent ? 100 : 1;
  const delta = first && last && first !== last ? ((last.value ?? 0) - (first.value ?? 0)) * scale : null;
  const meaningful = delta !== null && Math.abs(delta) > NOISE_POINTS;

  let note: string;
  if (numeric.length < 2 || delta === null) {
    note = "One reading so far: this is your baseline.";
  } else if (!meaningful) {
    note = `${delta >= 0 ? "+" : "−"}${Math.abs(delta).toFixed(1)} points since the first scan: within day-to-day variation.`;
  } else if (meta.lowerIsFuller) {
    note =
      delta < 0
        ? `Down ${Math.abs(delta).toFixed(1)} points since the first scan: consistent with fuller coverage, if the lighting matched.`
        : `Up ${delta.toFixed(1)} points since the first scan. Confirm on the next scan before reading anything into it.`;
  } else {
    note = `${delta > 0 ? "Up" : "Down"} ${Math.abs(delta).toFixed(1)} points since the first scan. Confirm on the next scan before reading anything into it.`;
  }

  // Chart geometry
  const w = 640;
  const h = 150;
  const padX = 18;
  const padY = 18;
  const vals = numeric.map((p) => p.value as number);
  const lo = vals.length ? Math.min(...vals) : 0;
  const hi = vals.length ? Math.max(...vals) : 1;
  const span = hi - lo;
  const min = lo - (span > 0 ? span * 0.4 : 0.03);
  const max = hi + (span > 0 ? span * 0.4 : 0.03);
  const x = (i: number) => (points.length === 1 ? w / 2 : padX + (i * (w - padX * 2)) / (points.length - 1));
  const y = (v: number) => h - padY - ((v - min) / (max - min || 1)) * (h - padY * 2);
  const path = points
    .map((p, i) => (p.value === null ? null : `${i === 0 ? "M" : "L"} ${x(i).toFixed(1)} ${y(p.value).toFixed(1)}`))
    .filter(Boolean)
    .join(" ");
  const fmt = (v: number) => (meta.percent ? `${(v * 100).toFixed(1)}%` : v.toFixed(2));

  return (
    <figure>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="text-2xl">
            <MetricTerm kind={kind} label={meta.title} />
          </h2>
          <p className="mt-1 text-sm text-ink-soft">{meta.subtitle}</p>
        </div>
        <div className="text-right">
          <p className="label">Latest</p>
          {last.value !== null && meta.percent ? (
            <Readout value={last.value * 100} digits={1} suffix="%" className="text-3xl font-medium tracking-[-0.04em]" />
          ) : (
            <p className="font-display text-3xl">{last.label ? String(last.label).replace(/^apparent /, "").replace(/ \(see limitations\)$/, "") : last.value?.toFixed(2) ?? "—"}</p>
          )}
          <div className="mt-1 flex justify-end">
            <ConfidenceChip value={last.confidence} />
          </div>
        </div>
      </div>

      <div className="crop-marks mt-4">
        <div className="graph-paper border border-rule bg-surface px-2 pb-2 pt-3">
          <svg viewBox={`0 0 ${w} ${h}`} className="h-36 w-full overflow-visible" role="img" aria-label={`${meta.title} across ${points.length} scans`}>
            {vals.length > 0 && (
              <>
                <line x1={padX} x2={w - padX} y1={y(hi)} y2={y(hi)} className="stroke-rule-strong" strokeDasharray="2 4" />
                <line x1={padX} x2={w - padX} y1={y(lo)} y2={y(lo)} className="stroke-rule-strong" strokeDasharray="2 4" />
                <text x={w - padX} y={y(hi) - 5} textAnchor="end" className="fill-ink-faint font-mono text-[10px]">
                  {fmt(hi)}
                </text>
                <text x={w - padX} y={y(lo) + 13} textAnchor="end" className="fill-ink-faint font-mono text-[10px]">
                  {fmt(lo)}
                </text>
              </>
            )}
            {path && <path d={path} fill="none" className="stroke-ink" strokeWidth={1.75} strokeLinejoin="round" />}
            {points.map((p, i) =>
              p.value === null ? null : (
                <rect
                  key={i}
                  x={x(i) - 3.5}
                  y={y(p.value) - 3.5}
                  width={7}
                  height={7}
                  className={i === points.length - 1 ? "fill-marker stroke-ink" : "fill-surface stroke-ink"}
                  strokeWidth={1.5}
                >
                  <title>
                    {new Date(p.date).toLocaleDateString()}: {fmt(p.value)} ({Math.round(p.confidence * 100)}% confidence)
                  </title>
                </rect>
              )
            )}
          </svg>
          <div className="flex justify-between px-2 pt-1">
            {points.map((p, i) => (
              <span key={i} className="readout text-[10px] text-ink-faint">
                {new Date(p.date).toLocaleDateString(undefined, { day: "numeric", month: "short" })}
              </span>
            ))}
          </div>
        </div>
      </div>
      <figcaption className="caption mt-2.5 flex flex-wrap justify-between gap-x-6 gap-y-1">
        <span>
          Fig. {index} · {meta.title}, {points.length} scan{points.length === 1 ? "" : "s"}
        </span>
        <span className="text-ink-soft">{note}</span>
      </figcaption>
    </figure>
  );
}
