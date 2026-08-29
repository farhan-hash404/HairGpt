"use client";

import * as React from "react";
import { Check, Minus, TrendingDown, TrendingUp } from "lucide-react";
import { api, type SheddingEntry, type SheddingTrend } from "@/lib/api";
import { AuthGate } from "@/components/auth-gate";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { titleize } from "@/lib/utils";

export default function SheddingPage() {
  return (
    <AuthGate>
      <Shedding />
    </AuthGate>
  );
}

const CONTEXTS = [
  { value: "wash", label: "Washing" },
  { value: "brush", label: "Brushing" },
  { value: "pillow", label: "Pillow" },
  { value: "general", label: "Through the day" },
];

// Counting individual hairs is tedious, so buckets keep daily logging realistic.
const BUCKETS = [
  { value: "none", label: "Barely any" },
  { value: "light", label: "A little" },
  { value: "moderate", label: "Noticeable" },
  { value: "heavy", label: "A lot" },
  { value: "very_heavy", label: "Alarming" },
];

function Shedding() {
  const [entries, setEntries] = React.useState<SheddingEntry[]>([]);
  const [trend, setTrend] = React.useState<SheddingTrend | null>(null);
  const [context, setContext] = React.useState("wash");
  const [bucket, setBucket] = React.useState<string | null>(null);
  const [count, setCount] = React.useState("");
  const [saved, setSaved] = React.useState(false);
  const [busy, setBusy] = React.useState(false);
  const [showAll, setShowAll] = React.useState(false);

  const load = React.useCallback(async () => {
    setEntries(await api.listShedding(90));
    setTrend(await api.sheddingTrend(60));
  }, []);

  React.useEffect(() => {
    load();
  }, [load]);

  async function submit() {
    if (!bucket && !count) return;
    setBusy(true);
    try {
      await api.logShedding({
        context,
        bucket,
        count: count ? Number(count) : null,
        washed_hair: context === "wash",
      });
      setSaved(true);
      setCount("");
      setBucket(null);
      await load();
      setTimeout(() => setSaved(false), 2000);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Shedding log</h1>
        <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
          You&apos;ll notice shedding long before a photo shows anything. Logging it takes a few seconds and gives your
          timeline an early signal — and your clinician something concrete.
        </p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Log today</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <p className="mb-2 text-sm font-medium">When did you notice it?</p>
            <div className="flex flex-wrap gap-2">
              {CONTEXTS.map((c) => (
                <button
                  key={c.value}
                  onClick={() => setContext(c.value)}
                  className={`rounded-full border px-3 py-1.5 text-sm transition-colors ${
                    context === c.value
                      ? "border-primary bg-primary/10 text-primary"
                      : "text-muted-foreground hover:bg-muted"
                  }`}
                >
                  {c.label}
                </button>
              ))}
            </div>
            <p className="mt-1.5 text-xs text-muted-foreground">
              Shedding is naturally much higher on wash days, so we only ever compare like with like.
            </p>
          </div>

          <div>
            <p className="mb-2 text-sm font-medium">How much?</p>
            <div className="flex flex-wrap gap-2">
              {BUCKETS.map((b) => (
                <button
                  key={b.value}
                  onClick={() => setBucket(b.value)}
                  className={`rounded-full border px-3 py-1.5 text-sm transition-colors ${
                    bucket === b.value
                      ? "border-primary bg-primary/10 text-primary"
                      : "text-muted-foreground hover:bg-muted"
                  }`}
                >
                  {b.label}
                </button>
              ))}
            </div>
          </div>

          <label className="block text-sm">
            <span className="mb-1 block font-medium">Or an exact count, if you counted</span>
            <input
              type="number"
              min={0}
              value={count}
              onChange={(e) => setCount(e.target.value)}
              placeholder="optional"
              className="w-40 rounded-xl border bg-background px-3 py-2 outline-none focus-visible:ring-2 focus-visible:ring-ring"
            />
          </label>

          <div className="flex items-center gap-3">
            <Button onClick={submit} disabled={busy || (!bucket && !count)}>
              {busy ? "Saving…" : "Log it"}
            </Button>
            {saved && (
              <span className="flex items-center gap-1.5 text-sm text-primary">
                <Check className="h-4 w-4" /> Logged
              </span>
            )}
          </div>
        </CardContent>
      </Card>

      {trend && <TrendCard trend={trend} entries={entries} />}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Recent entries</CardTitle>
        </CardHeader>
        <CardContent>
          {entries.length === 0 ? (
            <p className="text-sm text-muted-foreground">Nothing logged yet.</p>
          ) : (
            <>
              <ul className="divide-y">
                {[...entries]
                  .reverse()
                  .slice(0, showAll ? undefined : 12)
                  .map((e) => (
                    <li key={e.id} className="flex items-center justify-between py-2.5 text-sm">
                      <span>{e.date ? new Date(e.date).toLocaleDateString() : "—"}</span>
                      <span className="flex items-center gap-2">
                        <Badge variant="secondary">{titleize(e.context)}</Badge>
                        <span className="tabular-nums text-muted-foreground">
                          {e.count !== null ? `${e.count} hairs` : e.bucket ? titleize(e.bucket) : "—"}
                        </span>
                      </span>
                    </li>
                  ))}
              </ul>
              {entries.length > 12 && (
                <Button variant="ghost" size="sm" className="mt-3" onClick={() => setShowAll((s) => !s)}>
                  {showAll ? "Show less" : `Show all ${entries.length} entries`}
                </Button>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

/** One line per context, because wash-day and brush-day counts live on
 *  completely different scales and must never share an axis. */
function ContextChart({ entries, context }: { entries: SheddingEntry[]; context: string }) {
  const points = entries
    .filter((e) => e.context === context && e.count !== null)
    .map((e) => ({ date: e.date!, value: e.count! }));
  if (points.length < 2) return null;

  const values = points.map((p) => p.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const pad = (max - min) * 0.15 || 5;
  const lo = min - pad;
  const hi = max + pad;

  const w = 600;
  const h = 70;
  const inset = 6;
  const x = (i: number) => inset + (i * (w - inset * 2)) / (points.length - 1);
  const y = (v: number) => h - inset - ((v - lo) / (hi - lo || 1)) * (h - inset * 2);
  const path = points.map((p, i) => `${i === 0 ? "M" : "L"} ${x(i)} ${y(p.value)}`).join(" ");

  return (
    <div>
      <div className="mb-1 flex items-baseline justify-between text-xs">
        <span className="font-medium">{titleize(context)} days</span>
        <span className="tabular-nums text-muted-foreground">
          {min}–{max} hairs
        </span>
      </div>
      <svg viewBox={`0 0 ${w} ${h}`} className="h-16 w-full" role="img" aria-label={`${context} shedding over time`}>
        <path d={path} fill="none" stroke="hsl(var(--primary))" strokeWidth={2} strokeLinecap="round" />
      </svg>
    </div>
  );
}

function TrendCard({ trend, entries }: { trend: SheddingTrend; entries: SheddingEntry[] }) {
  const config = {
    increasing: { icon: TrendingUp, tone: "text-[hsl(var(--caution))]", label: "Appears to be increasing" },
    decreasing: { icon: TrendingDown, tone: "text-primary", label: "Appears to be decreasing" },
    stable: { icon: Minus, tone: "text-muted-foreground", label: "No detectable change" },
    insufficient_data: { icon: Minus, tone: "text-muted-foreground", label: "Not enough data yet" },
  }[trend.trend];
  const Icon = config.icon;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Icon className={`h-4 w-4 ${config.tone}`} />
          {config.label}
        </CardTitle>
        <p className="text-sm text-muted-foreground">{trend.trend_note}</p>
      </CardHeader>
      <CardContent className="space-y-3">
        {Object.keys(trend.average_by_context).length > 0 && (
          <div className="grid gap-3 sm:grid-cols-2">
            {Object.entries(trend.average_by_context).map(([ctx, avg]) => (
              <div key={ctx} className="rounded-xl border p-3">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">{titleize(ctx)}</p>
                <p className="mt-0.5 text-xl font-semibold tabular-nums">{avg}</p>
                <p className="text-xs text-muted-foreground">average over {trend.window_days} days</p>
              </div>
            ))}
          </div>
        )}

        <div className="space-y-3">
          {Object.keys(trend.average_by_context).map((ctx) => (
            <ContextChart key={ctx} entries={entries} context={ctx} />
          ))}
        </div>

        <p className="text-xs text-muted-foreground">{trend.disclaimer}</p>
      </CardContent>
    </Card>
  );
}
