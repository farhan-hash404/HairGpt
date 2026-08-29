"use client";

import * as React from "react";
import { useParams } from "next/navigation";
import { Printer } from "lucide-react";
import { api } from "@/lib/api";
import { AuthGate } from "@/components/auth-gate";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { titleize } from "@/lib/utils";

export default function ReportPage() {
  return (
    <AuthGate>
      <Report />
    </AuthGate>
  );
}

function Report() {
  const { id } = useParams<{ id: string }>();
  const [r, setR] = React.useState<any>(null);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    api.doctorReport(id).then(setR).catch((e) => setError(e?.message ?? "Could not load report"));
  }, [id]);

  if (error) return <p className="text-destructive">{error}</p>;
  if (!r) return <p className="text-muted-foreground">Preparing report…</p>;

  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <header className="flex flex-wrap items-start justify-between gap-3 print:hidden">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Clinician-facing draft</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Share this with your clinician. It is a discussion aid, not a diagnosis.
          </p>
        </div>
        <Button onClick={() => window.print()} variant="outline">
          <Printer className="h-4 w-4" /> Print / save PDF
        </Button>
      </header>

      <Card>
        <CardHeader>
          <CardTitle className="flex flex-wrap items-center gap-2">
            HairGPT summary — {titleize(r.domain)}
            <Badge variant="destructive">not a diagnosis</Badge>
          </CardTitle>
          <p className="text-sm text-muted-foreground">
            Captured {new Date(r.captured_at).toLocaleString()} · overall interpretation confidence{" "}
            {Math.round(r.overall_confidence * 100)}%
          </p>
        </CardHeader>
        <CardContent className="space-y-5">
          <section>
            <h2 className="mb-1 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
              Image-based observations
            </h2>
            <p className="mb-2 text-xs text-muted-foreground">
              One row per capture view — repeated observation kinds reflect independent measurements of different
              views, not repeated readings of the same image.
            </p>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="text-left text-xs uppercase tracking-wide text-muted-foreground">
                  <tr>
                    <th className="py-2">View</th>
                    <th className="py-2">Observation</th>
                    <th className="py-2">Value</th>
                    <th className="py-2">Type</th>
                    <th className="py-2">Confidence</th>
                    <th className="py-2">Model</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {r.observations.map((o: any, i: number) => (
                    <tr key={i}>
                      <td className="py-2 text-xs text-muted-foreground">{o.view ? titleize(o.view) : "—"}</td>
                      <td className="py-2">{titleize(o.kind)}</td>
                      <td className="py-2 tabular-nums">
                        {o.value_label ?? (o.value_num !== null ? `${o.value_num} ${o.unit ?? ""}` : "—")}
                      </td>
                      <td className="py-2">{o.observation_type.replace("_", " ")}</td>
                      <td className="py-2 tabular-nums">{Math.round(o.confidence * 100)}%</td>
                      <td className="py-2 text-xs text-muted-foreground">
                        {o.model_version} {o.is_mock && <Badge variant="mock">mock</Badge>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          {r.safety_verdict && (
            <section>
              <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                Safety screening
              </h2>
              <p className="text-sm">
                Verdict: <strong>{r.safety_verdict.verdict}</strong> — {r.safety_verdict.message}
              </p>
              {!!r.safety_verdict.red_flags?.length && (
                <p className="mt-1 text-sm text-muted-foreground">
                  Flags: {r.safety_verdict.red_flags.map((f: string) => f.replace(/_/g, " ")).join(", ")}
                </p>
              )}
            </section>
          )}

          <section>
            <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
              Points for discussion
            </h2>
            <ul className="space-y-2 text-sm">
              {r.recommendations.map((rec: any, i: number) => (
                <li key={i}>
                  <span className="font-medium">{rec.title}</span> — {rec.body}
                  {!!rec.evidence?.length && (
                    <span className="text-xs text-muted-foreground">
                      {" "}
                      [{rec.evidence.map((e: any) => e.source).join(", ")}]
                    </span>
                  )}
                </li>
              ))}
            </ul>
          </section>

          <section className="rounded-xl bg-muted/50 p-4">
            <h2 className="mb-2 text-sm font-semibold">Important limitations</h2>
            <ul className="space-y-1 text-xs text-muted-foreground">
              {r.disclaimers.map((d: string, i: number) => (
                <li key={i}>• {d}</li>
              ))}
            </ul>
          </section>
        </CardContent>
      </Card>
    </div>
  );
}
