"use client";

import * as React from "react";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { api } from "@/lib/api";
import { AuthGate } from "@/components/auth-gate";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { ConfidenceChip } from "@/components/confidence";
import { ComparePanes } from "@/components/compare-panes";
import { PageHeader } from "@/components/page-header";
import { WhyEvidence } from "@/components/why-evidence";
import { ReticleMark } from "@/components/wordmark";
import { titleize } from "@/lib/utils";

export default function ComparePage() {
  return (
    <AuthGate>
      <Compare />
    </AuthGate>
  );
}

function Compare() {
  const [scans, setScans] = React.useState<any[]>([]);
  const [before, setBefore] = React.useState("");
  const [after, setAfter] = React.useState("");
  const [result, setResult] = React.useState<any>(null);
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    api.listScans().then((l) => {
      const complete = l.filter((s: any) => s.status === "complete");
      setScans(complete);
      if (complete.length >= 2) {
        setBefore(complete[complete.length - 1].id);
        setAfter(complete[0].id);
      }
    });
  }, []);

  async function run() {
    setBusy(true);
    setError(null);
    try {
      setResult(await api.compare(before, after));
    } catch (e: any) {
      setError(e?.message ?? "Comparison failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-5xl animate-rise">
      <PageHeader
        index="Nº 05"
        eyebrow="Compare · two scans, one frame"
        title={
          <>
            Before, after, and <span className="marker">the difference</span>.
          </>
        }
        dek="Both photographs are aligned to a standard frame first. These are apparent changes; photographs cannot prove a treatment worked."
      />

      {scans.length < 2 ? (
        <div className="crop-marks mx-auto max-w-xl">
          <div className="graph-paper border border-rule bg-surface px-6 py-12 text-center">
            <ReticleMark className="mx-auto h-12 w-12 text-ink-faint" />
            <p className="mt-4 font-display text-2xl">Two scans needed.</p>
            <p className="mx-auto mt-2 max-w-sm text-sm text-ink-soft">
              A comparison needs two completed scans of the same view, ideally 30 days or more apart.
            </p>
            <Link href="/assessment" className={buttonVariants({ className: "mt-6" })}>
              Take a scan
            </Link>
          </div>
        </div>
      ) : (
        <div className="flex flex-wrap items-end gap-3 border-y border-rule py-5">
          <ScanSelect label="Before" value={before} onChange={setBefore} options={scans} />
          <ArrowRight className="mb-3 hidden h-4 w-4 text-ink-faint sm:block" />
          <ScanSelect label="After" value={after} onChange={setAfter} options={scans} />
          <Button onClick={run} disabled={busy || !before || !after || before === after} className="sm:ml-auto">
            {busy ? "Aligning…" : "Compare"}
          </Button>
        </div>
      )}

      {error && (
        <p role="alert" className="mt-4 border-l-2 border-alert bg-alert-wash px-4 py-3 text-sm text-alert">
          {error}
        </p>
      )}

      {result && (
        <div className="mt-10 space-y-12">
          <ComparePanes
            sessionBefore={result.session_before}
            sessionAfter={result.session_after}
            view={result.explanation?.compared_view ?? null}
            alignmentQuality={result.alignment_quality}
          />

          <section>
            <div className="mb-4 flex flex-wrap items-baseline justify-between gap-3">
              <h2 className="flex items-baseline gap-3 text-2xl">
                <span className="readout text-sm text-ink-faint">A.</span>
                Apparent changes
              </h2>
              <Badge variant={result.alignment_quality >= 0.5 ? "neutral" : "caution"}>
                alignment {Math.round(result.alignment_quality * 100)}%
              </Badge>
            </div>
            {result.metrics?.length ? (
              <div className="overflow-x-auto border-t border-ink">
                <table className="w-full min-w-[34rem] text-sm">
                  <thead>
                    <tr className="border-b border-rule text-left">
                      {["Metric", "Before", "After", "Change", "Confidence"].map((h) => (
                        <th key={h} className="label py-2.5 pr-4 font-medium">
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {result.metrics.map((m: any) => (
                      <tr key={m.kind} className="border-b border-rule">
                        <td className="py-3 pr-4">
                          <span className="font-display text-base">{titleize(m.kind)}</span>
                          {m.is_mock && (
                            <Badge variant="flag" className="ml-2">
                              mock
                            </Badge>
                          )}
                        </td>
                        <td className="readout py-3 pr-4">{m.before}</td>
                        <td className="readout py-3 pr-4">{m.after}</td>
                        <td className="py-3 pr-4">
                          <span className="readout">
                            {m.delta > 0 ? "+" : ""}
                            {m.delta}
                          </span>{" "}
                          <span className="caption">{m.direction.replace("_", " ")}</span>
                        </td>
                        <td className="py-3">
                          <ConfidenceChip value={m.confidence} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="border-y border-rule py-5 text-sm text-ink-soft">
                No comparable numeric metrics between these two scans.
              </p>
            )}
            <WhyEvidence className="mt-5" explain={result.explanation} />
          </section>

          {!!result.limitations?.length && (
            <section className="border-l-2 border-caution bg-caution-wash px-5 py-4">
              <p className="label mb-2 text-caution">Limitations of this comparison</p>
              <ul className="space-y-1.5 text-sm leading-relaxed text-ink-soft">
                {result.limitations.map((l: string, i: number) => (
                  <li key={i} className="grid grid-cols-[1.25rem_1fr]">
                    <span className="readout text-xs text-ink-faint">{i + 1}</span>
                    <span>{l}</span>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </div>
      )}
    </div>
  );
}

function ScanSelect({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: any[];
}) {
  return (
    <label className="block">
      <span className="label mb-1.5 block">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="readout min-w-[13rem] rounded border border-rule-strong bg-surface px-3 py-2.5 text-sm focus:border-ink focus:outline-none focus:ring-2 focus:ring-marker/70"
      >
        {options.map((s) => (
          <option key={s.id} value={s.id}>
            {new Date(s.created_at).toLocaleDateString(undefined, { day: "2-digit", month: "short", year: "numeric" })} · {s.domain}
          </option>
        ))}
      </select>
    </label>
  );
}
