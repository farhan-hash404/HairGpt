"use client";

import * as React from "react";
import { useParams } from "next/navigation";
import { Printer } from "lucide-react";
import { api } from "@/lib/api";
import { AuthGate } from "@/components/auth-gate";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ReticleMark } from "@/components/wordmark";
import { titleize } from "@/lib/utils";

export default function ReportPage() {
  return (
    <AuthGate>
      <Report />
    </AuthGate>
  );
}

function SectionHead({ n, title, note }: { n: number; title: string; note?: string }) {
  return (
    <div className="mb-3">
      <h2 className="flex items-baseline gap-3 text-xl">
        <span className="readout text-xs text-ink-faint">{n}.</span>
        {title}
      </h2>
      {note && <p className="caption mt-1">{note}</p>}
    </div>
  );
}

/** Self-reported history: usually the most clinically actionable part of this
 *  report, and the part whose value does not depend on model quality. */
function HistorySection({ n, history }: { n: number; history: any }) {
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
    rows.push(["Family history", `Positive${history.family_history_side ? ` (${history.family_history_side})` : ""}`]);
  }
  if (history.conditions?.length) rows.push(["Conditions", history.conditions.join(", ")]);
  if (history.possible_triggers?.length) {
    rows.push([
      "Possible triggers",
      `${history.possible_triggers.join(", ")}${history.trigger_months_ago ? ` — ~${history.trigger_months_ago} months ago` : ""}`,
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
      <SectionHead n={n} title="Self-reported history" note="Reported by the patient in-app. Not verified and not a diagnosis." />
      <dl className="border-t border-ink text-sm">
        {rows.map(([label, value]) => (
          <div key={label} className="grid grid-cols-[10rem_1fr] gap-4 border-b border-rule py-2.5">
            <dt className="label pt-0.5">{label}</dt>
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

  if (error) {
    return <p className="border-l-2 border-alert bg-alert-wash px-4 py-3 text-sm text-alert">{error}</p>;
  }
  if (!r) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center gap-3 text-ink-soft">
        <ReticleMark className="h-6 w-6 animate-spin text-ink [animation-duration:2.4s]" />
        <p className="label">Preparing report…</p>
      </div>
    );
  }

  let n = 0;
  const next = () => ++n;

  return (
    <div className="mx-auto max-w-3xl animate-rise">
      <header className="mb-8 flex flex-wrap items-end justify-between gap-4 print:hidden">
        <div>
          <p className="label mb-3">Doctor report</p>
          <h1 className="text-4xl">A summary to take with you.</h1>
          <p className="mt-2 font-display text-lg italic text-ink-soft">
            A discussion aid for your clinician, not a diagnosis.
          </p>
        </div>
        <Button onClick={() => window.print()} variant="outline">
          <Printer className="h-4 w-4" /> Print or save as PDF
        </Button>
      </header>

      <article className="crop-marks print:p-0 print:[background:none]">
        <div className="space-y-9 border border-rule bg-surface p-6 sm:p-10 print:border-0 print:p-0">
          {/* Letterhead */}
          <div className="flex flex-wrap items-start justify-between gap-4 border-b-2 border-ink pb-5">
            <div className="flex items-center gap-3">
              <ReticleMark className="h-9 w-9 text-ink" />
              <div>
                <p className="font-display text-2xl leading-none">HairGPT</p>
                <p className="label mt-1.5">Clinician-facing summary · {titleize(r.domain)}</p>
              </div>
            </div>
            <div className="text-right">
              <Badge variant="alert">not a diagnosis</Badge>
              <p className="caption mt-2">
                Captured {new Date(r.captured_at).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" })}
                <br />
                Interpretation confidence {Math.round(r.overall_confidence * 100)}%
              </p>
            </div>
          </div>

          {r.clinical_history && <HistorySection n={next()} history={r.clinical_history} />}

          {!!r.shedding_log_90d?.length && (
            <section>
              <SectionHead
                n={next()}
                title="Self-reported shedding, 90 days"
                note={`${r.shedding_log_90d.length} entries logged. Counts are patient estimates and vary with washing.`}
              />
              <ul className="grid border-t border-ink text-sm sm:grid-cols-2 sm:gap-x-8">
                {r.shedding_log_90d.slice(-8).map((s: any, i: number) => (
                  <li key={i} className="flex justify-between border-b border-rule py-2">
                    <span className="readout">{new Date(s.date).toLocaleDateString(undefined, { day: "2-digit", month: "short" })}</span>
                    <span className="text-ink-soft">
                      {titleize(s.context)} · {s.count !== null ? `${s.count} hairs` : titleize(s.bucket ?? "—")}
                    </span>
                  </li>
                ))}
              </ul>
            </section>
          )}

          <section>
            <SectionHead
              n={next()}
              title="Image-based observations"
              note="One row per capture view: repeated kinds are independent measurements of different views, not repeated readings of one image."
            />
            <div className="overflow-x-auto border-t border-ink">
              <table className="w-full min-w-[36rem] text-sm">
                <thead>
                  <tr className="border-b border-rule text-left">
                    {["View", "Observation", "Value", "Type", "Conf.", "Model"].map((h) => (
                      <th key={h} className="label py-2 pr-3 font-medium">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {r.observations.map((o: any, i: number) => (
                    <tr key={i} className="border-b border-rule">
                      <td className="py-2 pr-3 text-xs text-ink-soft">{o.view ? titleize(o.view) : "—"}</td>
                      <td className="py-2 pr-3">{titleize(o.kind)}</td>
                      <td className="readout py-2 pr-3 text-xs">
                        {o.value_label ?? (o.value_num !== null ? `${o.value_num} ${o.unit ?? ""}` : "—")}
                      </td>
                      <td className="py-2 pr-3 text-xs">{o.observation_type.replace("_", " ")}</td>
                      <td className="readout py-2 pr-3 text-xs">{Math.round(o.confidence * 100)}%</td>
                      <td className="py-2 text-xs text-ink-soft">
                        <span className="readout">{o.model_version}</span> {o.is_mock && <Badge variant="flag">mock</Badge>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          {r.safety_verdict && (
            <section>
              <SectionHead n={next()} title="Safety screening" />
              <p className="border-t border-ink pt-3 text-sm">
                Verdict: <strong className="readout uppercase">{r.safety_verdict.verdict}</strong> — {r.safety_verdict.message}
              </p>
              {!!r.safety_verdict.red_flags?.length && (
                <p className="mt-1.5 text-sm text-ink-soft">
                  Flags: {r.safety_verdict.red_flags.map((f: string) => f.replace(/_/g, " ")).join(", ")}
                </p>
              )}
            </section>
          )}

          <section>
            <SectionHead n={next()} title="Points for discussion" />
            <ol className="border-t border-ink text-sm">
              {r.recommendations.map((rec: any, i: number) => (
                <li key={i} className="grid grid-cols-[2rem_1fr] gap-2 border-b border-rule py-2.5">
                  <span className="readout text-xs text-ink-faint">{String(i + 1).padStart(2, "0")}</span>
                  <span>
                    <span className="font-medium">{rec.title}</span> — {rec.body}
                    {!!rec.evidence?.length && (
                      <span className="caption"> [{rec.evidence.map((e: any) => e.source).join(", ")}]</span>
                    )}
                  </span>
                </li>
              ))}
            </ol>
          </section>

          <section className="border-t border-rule pt-4">
            <p className="label mb-2">Important limitations</p>
            <ol className="space-y-1">
              {r.disclaimers.map((d: string, i: number) => (
                <li key={i} className="grid grid-cols-[1.25rem_1fr] text-xs leading-relaxed text-ink-soft">
                  <span className="readout text-ink-faint">{i + 1}</span>
                  <span>{d}</span>
                </li>
              ))}
            </ol>
          </section>
        </div>
      </article>
    </div>
  );
}
