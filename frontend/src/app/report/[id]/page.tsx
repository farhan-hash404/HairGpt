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

/** Self-reported history — usually the most clinically actionable part of this
 *  report, and the part whose value does not depend on model quality. */
function HistorySection({ history }: { history: any }) {
  const rows: [string, React.ReactNode][] = [];

  if (history.onset || history.pattern || history.duration_months) {
    rows.push([
      "Presentation",
      [
        history.onset && `${titleize(history.onset)} onset`,
        history.pattern && `${titleize(history.pattern)} pattern`,
        history.duration_months && `${history.duration_months} months`,
      ]
        .filter(Boolean)
        .join(" · "),
    ]);
  }
  if (history.family_history_hair_loss) {
    rows.push([
      "Family history",
      `Positive${history.family_history_side ? ` (${history.family_history_side})` : ""}`,
    ]);
  }
  if (history.conditions?.length) rows.push(["Conditions", history.conditions.join(", ")]);
  if (history.possible_triggers?.length) {
    rows.push([
      "Possible triggers",
      `${history.possible_triggers.join(", ")}${
        history.trigger_months_ago ? ` — ~${history.trigger_months_ago} months ago` : ""
      }`,
    ]);
  }
  if (history.medications?.length) rows.push(["Medications", history.medications.join(", ")]);
  if (history.medications_associated_with_shedding?.length) {
    rows.push([
      "Shedding-associated",
      <span key="flag" className="text-caution">
        {history.medications_associated_with_shedding.join(", ")} — association only, not causation
      </span>,
    ]);
  }
  if (history.styling?.length) rows.push(["Hair care", history.styling.join(", ")]);
  if (history.symptoms?.length) rows.push(["Symptoms", history.symptoms.join(", ")]);
  if (history.notes) rows.push(["Patient notes", history.notes]);

  if (!rows.length) return null;

  return (
    <section>
      <h2 className="mb-1 text-sm font-semibold uppercase tracking-wide text-ink-soft">
        Self-reported history
      </h2>
      <p className="mb-2 text-xs text-ink-soft">
        Reported by the patient in-app. Not verified and not a diagnosis.
      </p>
      <dl className="grid gap-2 text-sm">
        {rows.map(([label, value]) => (
          <div key={label} className="grid grid-cols-[9rem_1fr] gap-3 border-b pb-2">
            <dt className="text-ink-soft">{label}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

function Report() {
  const { id } = useParams<{ id: string }>();
  const [r, setR] = React.useState<any>(null);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    api.doctorReport(id).then(setR).catch((e) => setError(e?.message ?? "Could not load report"));
  }, [id]);

  if (error) return <p className="text-alert">{error}</p>;
  if (!r) return <p className="text-ink-soft">Preparing report…</p>;

  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <header className="flex flex-wrap items-start justify-between gap-3 print:hidden">
        <div>
          <h1 className="text-2xl font-normal">Clinician-facing draft</h1>
          <p className="mt-1 text-sm text-ink-soft">
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
            <Badge variant="alert">not a diagnosis</Badge>
          </CardTitle>
          <p className="text-sm text-ink-soft">
            Captured {new Date(r.captured_at).toLocaleString()} · overall interpretation confidence{" "}
            {Math.round(r.overall_confidence * 100)}%
          </p>
        </CardHeader>
        <CardContent className="space-y-5">
          {r.clinical_history && <HistorySection history={r.clinical_history} />}

          {!!r.shedding_log_90d?.length && (
            <section>
              <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-ink-soft">
                Self-reported shedding (90 days)
              </h2>
              <p className="text-sm text-ink-soft">
                {r.shedding_log_90d.length} entries logged. Counts are patient estimates and vary with washing.
              </p>
              <ul className="mt-2 grid gap-1 text-sm sm:grid-cols-2">
                {r.shedding_log_90d.slice(-8).map((s: any, i: number) => (
                  <li key={i} className="flex justify-between rounded-lg border px-3 py-1.5">
                    <span>{new Date(s.date).toLocaleDateString()}</span>
                    <span className="text-ink-soft">
                      {titleize(s.context)} · {s.count !== null ? `${s.count} hairs` : titleize(s.bucket ?? "—")}
                    </span>
                  </li>
                ))}
              </ul>
            </section>
          )}

          <section>
            <h2 className="mb-1 text-sm font-semibold uppercase tracking-wide text-ink-soft">
              Image-based observations
            </h2>
            <p className="mb-2 text-xs text-ink-soft">
              One row per capture view — repeated observation kinds reflect independent measurements of different
              views, not repeated readings of the same image.
            </p>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="text-left text-xs uppercase tracking-wide text-ink-soft">
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
                      <td className="py-2 text-xs text-ink-soft">{o.view ? titleize(o.view) : "—"}</td>
                      <td className="py-2">{titleize(o.kind)}</td>
                      <td className="py-2 tabular-nums">
                        {o.value_label ?? (o.value_num !== null ? `${o.value_num} ${o.unit ?? ""}` : "—")}
                      </td>
                      <td className="py-2">{o.observation_type.replace("_", " ")}</td>
                      <td className="py-2 tabular-nums">{Math.round(o.confidence * 100)}%</td>
                      <td className="py-2 text-xs text-ink-soft">
                        {o.model_version} {o.is_mock && <Badge variant="flag">mock</Badge>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          {r.safety_verdict && (
            <section>
              <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-ink-soft">
                Safety screening
              </h2>
              <p className="text-sm">
                Verdict: <strong>{r.safety_verdict.verdict}</strong> — {r.safety_verdict.message}
              </p>
              {!!r.safety_verdict.red_flags?.length && (
                <p className="mt-1 text-sm text-ink-soft">
                  Flags: {r.safety_verdict.red_flags.map((f: string) => f.replace(/_/g, " ")).join(", ")}
                </p>
              )}
            </section>
          )}

          <section>
            <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-ink-soft">
              Points for discussion
            </h2>
            <ul className="space-y-2 text-sm">
              {r.recommendations.map((rec: any, i: number) => (
                <li key={i}>
                  <span className="font-medium">{rec.title}</span> — {rec.body}
                  {!!rec.evidence?.length && (
                    <span className="text-xs text-ink-soft">
                      {" "}
                      [{rec.evidence.map((e: any) => e.source).join(", ")}]
                    </span>
                  )}
                </li>
              ))}
            </ul>
          </section>

          <section className="rounded bg-surface-sunken p-4">
            <h2 className="mb-2 text-sm font-semibold">Important limitations</h2>
            <ul className="space-y-1 text-xs text-ink-soft">
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
