"use client";

import * as React from "react";
import { Check, Minus, TrendingDown, TrendingUp } from "lucide-react";
import { api, type SheddingEntry, type SheddingTrend } from "@/lib/api";
import { AuthGate } from "@/components/auth-gate";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/page-header";
import { Readout } from "@/components/readout";
import { cn, titleize } from "@/lib/utils";

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

/** Connected switches, like the selector on an instrument. */
function Switches({
  options,
  value,
  onChange,
  label,
}: {
  options: { value: string; label: string }[];
  value: string | null;
  onChange: (v: string) => void;
  label: string;
}) {
  return (
    <div role="radiogroup" aria-label={label} className="inline-flex flex-wrap border border-rule-strong">
      {options.map((o, i) => {
        const active = value === o.value;
        return (
          <button
            key={o.value}
            type="button"
            role="radio"
            aria-checked={active}
            onClick={() => onChange(o.value)}
            className={cn(
              "px-3.5 py-2 text-sm transition-colors",
              i > 0 && "border-l border-rule-strong",
              active ? "bg-ink font-medium text-ground" : "bg-surface text-ink-soft hover:bg-surface-sunken hover:text-ink"
            )}
          >
            {o.label}
          </button>
        );
      })}
    </div>
  );
}

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
    <div className="mx-auto max-w-4xl animate-rise">
      <PageHeader
        index="Nº 03"
        eyebrow="Shedding log"
        title={
          <>
            What the <span className="marker">brush</span> noticed.
          </>
        }
        dek="You'll notice shedding long before a photograph shows anything. A few seconds a day gives your timeline an early signal, and your clinician something concrete."
      />

      <section className="crop-marks">
        <div className="space-y-6 border border-rule bg-surface p-5 sm:p-7">
          <p className="label">Today&apos;s entry</p>
          <div>
            <p className="mb-2.5 font-display text-lg">When did you notice it?</p>
            <Switches label="Context" options={CONTEXTS} value={context} onChange={setContext} />
            <p className="caption mt-2">Wash days shed far more, so only like is ever compared with like.</p>
          </div>

          <div>
            <p className="mb-2.5 font-display text-lg">How much?</p>
            <Switches label="Amount" options={BUCKETS} value={bucket} onChange={setBucket} />
          </div>

          <label className="block">
            <span className="mb-2 block font-display text-lg">
              Or an exact count <span className="text-base italic text-ink-faint">(if you counted)</span>
            </span>
            <input
              type="number"
              min={0}
              value={count}
              onChange={(e) => setCount(e.target.value)}
              placeholder="optional"
              className="readout w-40 rounded border border-rule-strong bg-surface px-3.5 py-2.5 text-base placeholder:font-sans placeholder:text-ink-faint focus:border-ink focus:outline-none focus:ring-2 focus:ring-marker/70"
            />
          </label>

          <div className="flex items-center gap-3 border-t border-rule pt-5">
            <Button onClick={submit} disabled={busy || (!bucket && !count)}>
              {busy ? "Saving…" : "Log it"}
            </Button>
            {saved && (
              <span className="marker inline-flex items-center gap-1.5 text-sm font-medium text-[hsl(30_12%_10%)]" role="status">
                <Check className="h-4 w-4" strokeWidth={2.5} /> Logged
              </span>
            )}
          </div>
        </div>
      </section>

      {trend && <TrendSection trend={trend} entries={entries} />}

      <section className="mt-14">
        <h2 className="mb-4 flex items-baseline gap-3 text-2xl">
          <span className="readout text-sm text-ink-faint">B.</span>
          Register
        </h2>
        {entries.length === 0 ? (
          <p className="border-y border-rule py-5 text-sm text-ink-soft">Nothing logged yet.</p>
        ) : (
          <>
            <ul className="border-t border-ink">
              {[...entries]
                .reverse()
                .slice(0, showAll ? undefined : 12)
                .map((e) => (
                  <li key={e.id} className="grid grid-cols-[8rem_1fr_auto] items-baseline gap-4 border-b border-rule py-3 text-sm">
                    <span className="readout text-ink-soft">
                      {e.date ? new Date(e.date).toLocaleDateString(undefined, { day: "2-digit", month: "short" }) : "—"}
                    </span>
                    <span className="label">{titleize(e.context)}</span>
                    <span className="readout">
                      {e.count !== null ? `${e.count} hairs` : e.bucket ? titleize(e.bucket) : "—"}
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
      </section>
    </div>
  );
}

/** One trace per context, because wash-day and brush-day counts live on
 *  completely different scales and must never share an axis. */
function ContextTrace({ entries, context }: { entries: SheddingEntry[]; context: string }) {
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
  const path = points.map((p, i) => `${i === 0 ? "M" : "L"} ${x(i).toFixed(1)} ${y(p.value).toFixed(1)}`).join(" ");

  return (
    <figure>
      <div className="graph-paper border border-rule bg-surface px-2 py-2">
        <svg viewBox={`0 0 ${w} ${h}`} className="h-16 w-full" role="img" aria-label={`${context} shedding over time`}>
          <path d={path} fill="none" className="stroke-ink" strokeWidth={1.5} strokeLinejoin="round" />
        </svg>
      </div>
      <figcaption className="caption mt-1.5 flex justify-between">
        <span>{titleize(context)} days</span>
        <span>
          {min}–{max} hairs
        </span>
      </figcaption>
    </figure>
  );
}

function TrendSection({ trend, entries }: { trend: SheddingTrend; entries: SheddingEntry[] }) {
  const config = {
    increasing: { icon: TrendingUp, tone: "text-caution", label: "Appears to be increasing." },
    decreasing: { icon: TrendingDown, tone: "text-ink", label: "Appears to be easing." },
    stable: { icon: Minus, tone: "text-ink", label: "No detectable change." },
    insufficient_data: { icon: Minus, tone: "text-ink-soft", label: "Not enough entries yet." },
  }[trend.trend];
  const Icon = config.icon;
  const contexts = Object.keys(trend.average_by_context);

  return (
    <section className="mt-14">
      <h2 className="mb-4 flex items-baseline gap-3 text-2xl">
        <span className="readout text-sm text-ink-faint">A.</span>
        Trend, last {trend.window_days} days
      </h2>
      <div className="border-t border-ink pt-5">
        <p className={cn("flex items-center gap-2.5 font-display text-3xl", config.tone)}>
          <Icon className="h-6 w-6 shrink-0" strokeWidth={1.75} />
          {config.label}
        </p>
        <p className="mt-2 max-w-[65ch] text-sm leading-relaxed text-ink-soft">{trend.trend_note}</p>

        {contexts.length > 0 && (
          <div className="mt-6 grid gap-px border border-rule bg-rule sm:grid-cols-2 lg:grid-cols-4">
            {Object.entries(trend.average_by_context).map(([ctx, avg]) => (
              <div key={ctx} className="bg-surface p-4">
                <p className="label">{titleize(ctx)}</p>
                <Readout value={Number(avg)} digits={Number.isInteger(Number(avg)) ? 0 : 1} className="mt-3 block text-3xl font-medium tracking-[-0.04em]" />
                <p className="caption mt-1">average hairs per entry</p>
              </div>
            ))}
          </div>
        )}

        <div className="mt-6 grid gap-5 sm:grid-cols-2">
          {contexts.map((ctx) => (
            <ContextTrace key={ctx} entries={entries} context={ctx} />
          ))}
        </div>

        <p className="caption mt-5 max-w-[80ch]">{trend.disclaimer}</p>
      </div>
    </section>
  );
}
