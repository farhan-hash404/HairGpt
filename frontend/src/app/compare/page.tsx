"use client";

import * as React from "react";
import { api } from "@/lib/api";
import { AuthGate } from "@/components/auth-gate";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ComparePanes } from "@/components/compare-panes";
import { WhyEvidence } from "@/components/why-evidence";
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
    <div className="mx-auto max-w-4xl space-y-6">
      <header>
        <h1 className="text-2xl font-normal">Compare scans</h1>
        <p className="mt-1 text-sm text-ink-soft">
          Photos are aligned to a standardized frame before comparison. Apparent changes only — images cannot prove
          treatment efficacy.
        </p>
      </header>

      {scans.length < 2 ? (
        <Card>
          <CardContent className="py-10 text-center text-ink-soft">
            You need at least two completed scans to compare.
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="flex flex-wrap items-end gap-3 pt-5">
            <Select label="Before" value={before} onChange={setBefore} options={scans} />
            <Select label="After" value={after} onChange={setAfter} options={scans} />
            <Button onClick={run} disabled={busy || !before || !after || before === after}>
              {busy ? "Aligning…" : "Compare"}
            </Button>
          </CardContent>
        </Card>
      )}

      {error && <p className="text-sm text-alert">{error}</p>}

      {result && (
        <>
          {/* Four synced panes: before | after | aligned overlay | difference */}
          <ComparePanes
            sessionBefore={result.session_before}
            sessionAfter={result.session_after}
            view={result.explanation?.compared_view ?? null}
            alignmentQuality={result.alignment_quality}
          />

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between gap-3">
                <span>Apparent changes</span>
                <Badge variant={result.alignment_quality >= 0.5 ? "default" : "caution"}>
                  alignment {Math.round(result.alignment_quality * 100)}%
                </Badge>
              </CardTitle>
            </CardHeader>
            <CardContent>
              {result.metrics?.length ? (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="text-left text-xs uppercase tracking-wide text-ink-soft">
                      <tr>
                        <th className="py-2">Metric</th>
                        <th className="py-2">Before</th>
                        <th className="py-2">After</th>
                        <th className="py-2">Change</th>
                        <th className="py-2">Confidence</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y">
                      {result.metrics.map((m: any) => (
                        <tr key={m.kind}>
                          <td className="py-2.5 font-medium">
                            {titleize(m.kind)}
                            {m.is_mock && <Badge variant="flag" className="ml-2">mock</Badge>}
                          </td>
                          <td className="py-2.5 tabular-nums">{m.before}</td>
                          <td className="py-2.5 tabular-nums">{m.after}</td>
                          <td className="py-2.5 tabular-nums">
                            {m.delta > 0 ? "+" : ""}
                            {m.delta} <span className="text-xs text-ink-soft">({m.direction.replace("_", " ")})</span>
                          </td>
                          <td className="py-2.5 tabular-nums">{Math.round(m.confidence * 100)}%</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="text-sm text-ink-soft">
                  No comparable numeric metrics between these two scans.
                </p>
              )}

              <div className="mt-4">
                <WhyEvidence explain={result.explanation} />
              </div>
            </CardContent>
          </Card>

          <Card className="border-caution/40 bg-caution-wash">
            <CardContent className="pt-5">
              <p className="mb-2 text-sm font-medium">Limitations of this comparison</p>
              <ul className="space-y-1 text-xs text-ink-soft">
                {result.limitations.map((l: string, i: number) => (
                  <li key={i}>• {l}</li>
                ))}
              </ul>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}

function Select({
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
    <label className="text-sm">
      <span className="mb-1 block font-medium">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded border bg-surface px-3 py-2"
      >
        {options.map((s) => (
          <option key={s.id} value={s.id}>
            {new Date(s.created_at).toLocaleDateString()} · {s.domain}
          </option>
        ))}
      </select>
    </label>
  );
}
