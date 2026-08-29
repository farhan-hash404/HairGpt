"use client";

import * as React from "react";
import Link from "next/link";
import { Camera, FileText, Sparkles } from "lucide-react";
import { api, type Analysis } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ConfidenceRing } from "@/components/confidence-ring";
import { MetricCard } from "@/components/metric-card";
import { WhyEvidence } from "@/components/why-evidence";
import { AuthGate } from "@/components/auth-gate";
import { pct } from "@/lib/utils";

/** Home dashboard — Apple-Health-like. Shows Hair Health, Hairline, Crown,
 *  Treatment adherence, Last scan, and Next recommended scan immediately. */
export default function HomePage() {
  return (
    <AuthGate>
      <Dashboard />
    </AuthGate>
  );
}

const SCAN_INTERVAL_DAYS = 30;

function Dashboard() {
  const [latest, setLatest] = React.useState<Analysis | null>(null);
  const [scans, setScans] = React.useState<any[]>([]);
  const [adherence, setAdherence] = React.useState<any[]>([]);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    (async () => {
      try {
        const list = await api.listScans();
        setScans(list);
        const complete = list.find((s: any) => s.status === "complete");
        if (complete) setLatest(await api.result(complete.id));
        setAdherence(await api.adherenceSummary());
      } catch {
        /* first-run: nothing yet */
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const lastScan = scans[0];
  const daysSince = lastScan ? Math.floor((Date.now() - new Date(lastScan.created_at).getTime()) / 86400000) : null;
  const nextIn = daysSince === null ? null : Math.max(0, SCAN_INTERVAL_DAYS - daysSince);
  const avgAdherence =
    adherence.length > 0 ? adherence.reduce((a, t) => a + t.adherence_pct, 0) / adherence.length : null;

  const hs = latest?.hair_summary ?? null;
  const anyMock = latest?.observations?.some((o) => o.is_mock) ?? false;

  if (loading) return <p className="text-muted-foreground">Loading your dashboard…</p>;

  if (!latest) return <EmptyState />;

  return (
    <div className="space-y-6">
      {/* Hero: Hair Health */}
      <Card className="overflow-hidden">
        <div className="flex flex-col gap-5 p-6 sm:flex-row sm:items-center sm:justify-between">
          <div className="min-w-0">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Hair Health</p>
            <h1 className="mt-1.5 text-3xl font-semibold tracking-tight">
              {describeOverall(latest.overall_confidence, hs)}
            </h1>
            <p className="mt-2 max-w-xl text-sm text-muted-foreground">
              {latest.explanation?.summary ?? "Based on your most recent scan."}
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              <Badge variant={latest.safety_verdict?.verdict === "refer" ? "destructive" : latest.safety_verdict?.verdict === "caution" ? "caution" : "default"}>
                safety: {latest.safety_verdict?.verdict ?? "—"}
              </Badge>
              {anyMock && <Badge variant="mock">mock inference · not validated</Badge>}
            </div>
          </div>
          <div className="flex items-center gap-4">
            <ConfidenceRing value={latest.overall_confidence} size={76} label="overall interpretation" />
            <div className="text-sm">
              <p className="font-medium">Overall confidence</p>
              <p className="text-muted-foreground">how sure the system is</p>
            </div>
          </div>
        </div>
        <div className="border-t bg-muted/30 p-5">
          <WhyEvidence explain={latest.explanation ?? undefined} evidence={latest.explanation?.evidence} />
        </div>
      </Card>

      {/* Metric grid */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <MetricCard
          label="Hairline"
          value={hs?.hairline_position?.label ? "Localized" : "—"}
          sublabel={hs?.hairline_position?.label ?? "No hairline reading in last scan"}
          confidence={hs?.hairline_position?.confidence ?? null}
          isMock={anyMock}
          href="/timeline"
        />
        <MetricCard
          label="Crown"
          value={hs?.crown_density?.label ?? "—"}
          sublabel="apparent crown density"
          confidence={hs?.crown_density?.confidence ?? null}
          isMock={anyMock}
          href="/timeline"
        />
        <MetricCard
          label="Scalp visibility"
          value={pct(hs?.scalp_visibility?.value ?? null)}
          sublabel="apparent fraction of visible scalp"
          confidence={hs?.scalp_visibility?.confidence ?? null}
          isMock={anyMock}
          href="/timeline"
        />
        <MetricCard
          label="Treatment adherence"
          value={avgAdherence === null ? "—" : `${avgAdherence.toFixed(0)}%`}
          sublabel={adherence.length ? `${adherence.length} active treatment(s)` : "No treatments tracked yet"}
          href="/treatments"
        />
        <MetricCard
          label="Last scan"
          value={daysSince === null ? "—" : daysSince === 0 ? "Today" : `${daysSince}d ago`}
          sublabel={lastScan ? new Date(lastScan.created_at).toLocaleDateString() : ""}
          href="/timeline"
        />
        <MetricCard
          label="Next recommended scan"
          value={nextIn === null ? "—" : nextIn === 0 ? "Now" : `in ${nextIn}d`}
          sublabel={`Consistent ${SCAN_INTERVAL_DAYS}-day intervals improve comparability`}
          tone="muted"
        />
      </div>

      {/* Actions */}
      <div className="flex flex-wrap gap-3">
        <Link href="/scan/hair">
          <Button size="lg">
            <Camera className="h-4 w-4" /> New scan
          </Button>
        </Link>
        <Link href="/compare">
          <Button size="lg" variant="outline">
            <Sparkles className="h-4 w-4" /> Compare with previous scan
          </Button>
        </Link>
        <Link href={`/report/${latest.session_id}`}>
          <Button size="lg" variant="outline">
            <FileText className="h-4 w-4" /> Doctor report
          </Button>
        </Link>
      </div>

      {!!latest.disclaimers?.length && (
        <Card className="bg-muted/40">
          <CardContent className="pt-5">
            <ul className="space-y-1 text-xs text-muted-foreground">
              {latest.disclaimers.map((d, i) => (
                <li key={i}>• {d}</li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function describeOverall(conf: number, hs: any) {
  const label = hs?.apparent_density?.label ?? hs?.crown_density?.label;
  if (conf < 0.4) return "Not enough signal yet";
  if (!label) return "Baseline recorded";
  return `Apparent: ${String(label).replace("apparent ", "")}`;
}

function EmptyState() {
  return (
    <div className="mx-auto max-w-2xl py-10 text-center">
      <div className="mx-auto mb-5 grid h-14 w-14 place-items-center rounded-2xl bg-accent">
        <Camera className="h-6 w-6 text-accent-foreground" />
      </div>
      <h1 className="text-2xl font-semibold tracking-tight">Start your first scan</h1>
      <p className="mx-auto mt-2 max-w-md text-muted-foreground">
        HairGPT guides you through 7 standardized views, checks image quality before analyzing, and tracks apparent
        changes over time — with confidence and sources on every conclusion.
      </p>
      <div className="mt-6 flex justify-center gap-3">
        <Link href="/scan/hair">
          <Button size="lg">
            <Camera className="h-4 w-4" /> Begin hair scan
          </Button>
        </Link>
        <Link href="/skin">
          <Button size="lg" variant="outline">
            SkinGPT
          </Button>
        </Link>
      </div>
    </div>
  );
}
