"use client";

import * as React from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { AuthGate } from "@/components/auth-gate";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { titleize } from "@/lib/utils";

type Point = { date: string; value: number | null; label: string | null; confidence: number; is_mock: boolean };

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

  if (!data) return <p className="text-muted-foreground">Loading timeline…</p>;

  const series: Record<string, Point[]> = data.series ?? {};
  const hasAny = Object.values(series).some((s) => s.length > 0);

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Longitudinal timeline</h1>
        <p className="mt-1 text-sm text-muted-foreground">{data.disclaimer}</p>
      </header>

      {!hasAny ? (
        <Card>
          <CardContent className="py-10 text-center text-muted-foreground">
            No completed scans yet.{" "}
            <Link href="/scan/hair" className="text-primary underline-offset-2 hover:underline">
              Run your first scan
            </Link>{" "}
            to start the timeline.
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4">
          {Object.entries(series).map(([kind, points]) =>
            points.length ? <Sparkline key={kind} kind={kind} points={points} /> : null
          )}
        </div>
      )}

      {/* Treatment lane */}
      <Card>
        <CardHeader>
          <CardTitle>Treatment timeline</CardTitle>
        </CardHeader>
        <CardContent>
          {data.treatments?.length ? (
            <ul className="space-y-2">
              {data.treatments.map((t: any) => {
                const a = adherence.find((x) => x.treatment_id === t.id);
                return (
                  <li key={t.id} className="flex flex-wrap items-center justify-between gap-2 rounded-xl border p-3">
                    <div>
                      <p className="font-medium">{t.name}</p>
                      <p className="text-xs text-muted-foreground">
                        {titleize(t.category)} · started {new Date(t.start_date).toLocaleDateString()}
                        {t.end_date ? ` · ended ${new Date(t.end_date).toLocaleDateString()}` : ""}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      {t.is_prescribed_by_clinician && <Badge variant="secondary">clinician-prescribed</Badge>}
                      {a && <Badge>{a.adherence_pct}% adherence</Badge>}
                    </div>
                  </li>
                );
              })}
            </ul>
          ) : (
            <p className="text-sm text-muted-foreground">
              No treatments tracked.{" "}
              <Link href="/treatments" className="text-primary underline-offset-2 hover:underline">
                Add one
              </Link>
              .
            </p>
          )}
        </CardContent>
      </Card>

      {/* Scan history */}
      <Card>
        <CardHeader>
          <CardTitle>Scan history</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="divide-y">
            {(data.scan_history ?? []).map((s: any) => (
              <li key={s.session_id} className="flex items-center justify-between py-2.5 text-sm">
                <Link href={`/scan/${s.session_id}/result`} className="hover:underline">
                  {new Date(s.date).toLocaleDateString()} · {titleize(s.domain)}
                </Link>
                <span className="text-muted-foreground tabular-nums">
                  {s.overall_confidence !== null ? `${Math.round(s.overall_confidence * 100)}% conf` : "—"}
                </span>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}

/**
 * Small-multiple sparkline. The y-axis zooms to the data range so small changes
 * are visible, but the range is ALWAYS labelled and the change is stated
 * numerically — a zoomed axis must never make a trivial change look dramatic.
 * Changes smaller than the measurement's own uncertainty are called out as such.
 */
function Sparkline({ kind, points }: { kind: string; points: Point[] }) {
  const vals = points.map((p) => p.value ?? 0);
  const dataMin = Math.min(...vals);
  const dataMax = Math.max(...vals);
  const span = dataMax - dataMin;
  // Pad the domain by 25% of the span (or a small floor when perfectly flat).
  const padDomain = span > 0 ? span * 0.25 : 0.02;
  const min = dataMin - padDomain;
  const max = dataMax + padDomain;

  const w = 600;
  const h = 90;
  const pad = 10;
  const x = (i: number) => (points.length === 1 ? w / 2 : pad + (i * (w - pad * 2)) / (points.length - 1));
  const y = (v: number) => h - pad - ((v - min) / (max - min || 1)) * (h - pad * 2);

  const anyMock = points.some((p) => p.is_mock);
  const path = points.map((p, i) => `${i === 0 ? "M" : "L"} ${x(i)} ${y(p.value ?? 0)}`).join(" ");
  const first = points[0];
  const last = points[points.length - 1];
  const delta = (last.value ?? 0) - (first.value ?? 0);

  // A change is only meaningful if it exceeds the uncertainty implied by the
  // weakest confidence in the pair. Below that, we say so plainly.
  const weakestConf = Math.min(first.confidence, last.confidence);
  const noiseFloor = (1 - weakestConf) * Math.max(Math.abs(dataMax), 0.05) * 0.5;
  const meaningful = Math.abs(delta) > noiseFloor;

  return (
    <Card>
      <CardContent className="pt-5">
        <div className="mb-2 flex flex-wrap items-baseline justify-between gap-2">
          <div>
            <p className="font-medium">{titleize(kind)}</p>
            <p className="text-xs text-muted-foreground">
              latest: {last.label ?? last.value ?? "—"} · confidence {Math.round(last.confidence * 100)}%
            </p>
          </div>
          {anyMock && <Badge variant="mock">mock · not validated</Badge>}
        </div>

        <div className="relative">
          {/* Axis range labels — the zoom is always disclosed. */}
          <div className="pointer-events-none absolute inset-y-0 right-0 flex flex-col justify-between py-1 text-[10px] tabular-nums text-muted-foreground">
            <span>{max.toFixed(3)}</span>
            <span>{min.toFixed(3)}</span>
          </div>
          <svg
            viewBox={`0 0 ${w} ${h}`}
            className="h-24 w-full pr-10"
            role="img"
            aria-label={`${titleize(kind)} over time, axis from ${min.toFixed(3)} to ${max.toFixed(3)}`}
          >
            <path
              d={path}
              fill="none"
              stroke="hsl(var(--primary))"
              strokeWidth={2}
              strokeLinecap="round"
              strokeDasharray={anyMock ? "5 4" : undefined}
            />
            {points.map((p, i) => (
              <circle
                key={i}
                cx={x(i)}
                cy={y(p.value ?? 0)}
                r={3.5}
                fill="hsl(var(--primary))"
                opacity={0.35 + p.confidence * 0.65}
              />
            ))}
          </svg>
        </div>

        <p className="mt-1 text-[11px] text-muted-foreground">
          {points.length > 1 && (
            <>
              Change over {points.length} scans:{" "}
              <span className="font-medium tabular-nums">
                {delta > 0 ? "+" : ""}
                {delta.toFixed(3)}
              </span>
              {" — "}
              {meaningful
                ? "larger than this measurement's uncertainty, but still an apparent change only."
                : "within measurement noise; treat as no detectable change."}{" "}
            </>
          )}
          Axis is zoomed to the data range (labelled at right). Opacity reflects confidence; dashed = mock inference.
        </p>
      </CardContent>
    </Card>
  );
}
