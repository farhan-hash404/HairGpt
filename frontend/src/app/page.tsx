"use client";

import * as React from "react";
import Link from "next/link";
import {
  AlertTriangle,
  ArrowRight,
  ArrowUpRight,
  Camera,
  CheckCircle2,
  FileText,
  Layers,
  Stethoscope,
} from "lucide-react";
import { api, modelTrustLabel, type Analysis } from "@/lib/api";
import { AuthGate } from "@/components/auth-gate";
import { buttonVariants } from "@/components/ui/button";
import { ConfidenceScale } from "@/components/confidence";
import { PageHeader } from "@/components/page-header";
import { PercentReadout, Readout } from "@/components/readout";
import { WhyEvidence } from "@/components/why-evidence";
import { ReticleMark } from "@/components/wordmark";
import { cn } from "@/lib/utils";

const SCAN_INTERVAL_DAYS = 30;

export default function OverviewPage() {
  return (
    <AuthGate>
      <Overview />
    </AuthGate>
  );
}

function Overview() {
  const [latest, setLatest] = React.useState<Analysis | null>(null);
  const [scans, setScans] = React.useState<any[]>([]);
  const [adherence, setAdherence] = React.useState<any[]>([]);
  const [shedding, setShedding] = React.useState<any>(null);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    (async () => {
      try {
        const list = await api.listScans();
        setScans(list);
        const complete = list.find((s: any) => s.status === "complete");
        if (complete) setLatest(await api.result(complete.id));
        setAdherence(await api.adherenceSummary());
        setShedding(await api.sheddingTrend(60));
      } catch {
        /* first run */
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  if (loading) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center">
        <div className="flex items-center gap-3 text-ink-soft">
          <ReticleMark className="h-6 w-6 animate-spin text-ink [animation-duration:2.4s]" />
          <p className="label">Loading your record…</p>
        </div>
      </div>
    );
  }

  if (!latest) return <FirstRun />;

  const lastScan = scans[0];
  const recordedAt = lastScan ? new Date(lastScan.created_at) : null;
  const daysSince = recordedAt ? Math.floor((Date.now() - recordedAt.getTime()) / 86400000) : null;
  const nextIn = daysSince === null ? null : Math.max(0, SCAN_INTERVAL_DAYS - daysSince);
  const avgAdherence =
    adherence.length > 0 ? adherence.reduce((a, t) => a + t.adherence_pct, 0) / adherence.length : null;

  const hs = latest.hair_summary ?? null;
  const trust = latest.observations?.length ? modelTrustLabel(latest.observations[0]) : null;
  const verdict = latest.safety_verdict?.verdict ?? "ok";
  const density = word(hs?.apparent_density?.label ?? hs?.crown_density?.label);
  const nextSteps = (latest.recommendations ?? []).filter((r) => r.title).slice(0, 4);

  return (
    <div className="animate-rise">
      <PageHeader
        index="Nº 01"
        eyebrow={recordedAt ? `Overview · recorded ${recordedAt.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" })}` : "Overview"}
        title={
          latest.overall_confidence < 0.4 ? (
            <>
              Baseline <span className="italic text-ink-soft">in progress.</span>
            </>
          ) : density ? (
            <>
              Apparent density reads <span className="marker">{density}</span>.
            </>
          ) : (
            "Baseline recorded."
          )
        }
        dek="From your most recent standardised capture. Every reading below states how sure it is."
        actions={
          <>
            <Link href="/assessment" className={buttonVariants()}>
              <Camera className="h-4 w-4" strokeWidth={2} />
              New check
            </Link>
            <Link href="/compare" className={buttonVariants({ variant: "outline" })}>
              <Layers className="h-4 w-4" strokeWidth={1.75} />
              Compare
            </Link>
            <Link href={`/report/${latest.session_id}`} className={buttonVariants({ variant: "outline" })}>
              <FileText className="h-4 w-4" strokeWidth={1.75} />
              Doctor report
            </Link>
          </>
        }
      />

      {/* Status strip: the four facts to read before any number. */}
      <section aria-label="Status" className="grid gap-px border border-rule bg-rule sm:grid-cols-2 lg:grid-cols-4">
        <StatusCell label="Safety screen">
          <VerdictLine verdict={verdict} />
        </StatusCell>
        <StatusCell label="Overall confidence">
          <ConfidenceScale value={latest.overall_confidence} label="this reading" size="sm" showLabel={false} />
        </StatusCell>
        <StatusCell label="Last capture">
          <p className="text-[0.95rem]">
            {daysSince === null ? "—" : daysSince === 0 ? "Today" : `${daysSince} day${daysSince === 1 ? "" : "s"} ago`}
          </p>
          <p className="caption mt-1">Next due {nextIn === null ? "—" : nextIn === 0 ? "now" : `in ${nextIn} days`}</p>
        </StatusCell>
        <StatusCell label="Model">
          <p className="text-[0.95rem]">{trust ? trust.text : "Validated model"}</p>
          <p className="caption mt-1">Readings are observations, not diagnoses</p>
        </StatusCell>
      </section>

      <Section letter="A" title="Measurements" more={{ href: "/timeline", label: "Timeline" }}>
        <div className="grid gap-px border border-rule bg-rule sm:grid-cols-2 lg:grid-cols-4">
          <Plate
            label="Apparent density"
            href="/timeline"
            value={<span className="font-display text-4xl leading-none">{word(hs?.apparent_density?.label) ?? "—"}</span>}
            caption={hs?.apparent_density?.value != null ? `Index ${hs.apparent_density.value.toFixed(2)} on a 0–1 scale` : "Whole-scalp coverage"}
            confidence={hs?.apparent_density?.confidence}
          />
          <Plate
            label="Crown"
            href="/timeline"
            value={<span className="font-display text-4xl leading-none">{word(hs?.crown_density?.label) ?? "—"}</span>}
            caption="Density at the crown swirl"
            confidence={hs?.crown_density?.confidence}
          />
          <Plate
            label="Scalp visibility"
            href="/timeline"
            value={<PercentReadout value={hs?.scalp_visibility?.value} className="text-4xl font-medium tracking-[-0.04em]" />}
            caption="Share of the frame where scalp shows through"
            confidence={hs?.scalp_visibility?.confidence}
          />
          <Plate
            label="Hairline"
            href="/timeline"
            value={<span className="font-display text-4xl leading-none">{hs?.hairline_position?.label ? "traced" : "—"}</span>}
            caption="Position recorded as your baseline; see limitations"
            confidence={hs?.hairline_position?.confidence}
          />
        </div>
      </Section>

      <Section letter="B" title="Regimen & progress" more={{ href: "/treatments", label: "Treatments" }}>
        <div className="grid gap-px border border-rule bg-rule sm:grid-cols-3">
          <Plate
            label="Adherence"
            href="/treatments"
            value={<Readout value={avgAdherence} suffix="%" className="text-4xl font-medium tracking-[-0.04em]" />}
            caption={
              adherence.length
                ? `Across ${adherence.length} active treatment${adherence.length === 1 ? "" : "s"}`
                : "No treatments recorded yet"
            }
          />
          <Plate
            label="Shedding"
            href="/shedding"
            value={<span className="font-display text-4xl leading-none">{sheddingWord(shedding)}</span>}
            caption={shedding?.trend_note ?? "Log daily counts to see a trend"}
          />
          <Plate
            label="Next check"
            href="/assessment"
            value={
              nextIn === 0 ? (
                <span className="font-display text-4xl leading-none">due now</span>
              ) : (
                <Readout value={nextIn} suffix=" days" className="text-4xl font-medium tracking-[-0.04em]" />
              )
            }
            caption={`${SCAN_INTERVAL_DAYS}-day spacing keeps hair cycles comparable`}
          />
        </div>
      </Section>

      <div className="mt-14 grid gap-10 lg:grid-cols-12">
        {nextSteps.length > 0 && (
          <section className="lg:col-span-5">
            <SectionTitle letter="C" title="Suggested next steps" />
            <ol className="mt-4 divide-y divide-rule border-y border-rule">
              {nextSteps.map((r, i) => (
                <li key={`${i}-${r.title}`} className="grid grid-cols-[2.25rem_1fr] gap-3 py-3.5">
                  <span className="readout pt-0.5 text-sm text-ink-faint">{String(i + 1).padStart(2, "0")}</span>
                  <span className="text-[0.95rem] leading-snug">{r.title}</span>
                </li>
              ))}
            </ol>
            <Link
              href={`/scan/${latest.session_id}/result`}
              className="mt-4 inline-flex items-center gap-1.5 text-sm font-medium text-accent underline decoration-accent/40 underline-offset-4 hover:decoration-accent"
            >
              Full result, with reasons
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </section>
        )}
        <section className={nextSteps.length > 0 ? "lg:col-span-7" : "lg:col-span-12"}>
          <SectionTitle letter={nextSteps.length > 0 ? "D" : "C"} title="Method & sources" />
          <div className="panel mt-4 p-5 sm:p-6">
            <p className="max-w-[62ch] text-sm leading-relaxed text-ink-soft">
              How each reading was made, how sure it is, what it cannot tell you, and the published sources behind
              every suggestion.
            </p>
            <WhyEvidence
              className="mt-4"
              explain={latest.explanation ?? undefined}
              evidence={latest.explanation?.evidence}
            />
          </div>
        </section>
      </div>
    </div>
  );
}

function word(label: string | null | undefined) {
  if (!label) return null;
  return String(label).replace(/^apparent |^crown appears /, "").trim() || null;
}

function sheddingWord(trend: any) {
  if (!trend || trend.trend === "insufficient_data") return "untracked";
  return { increasing: "rising", decreasing: "easing", stable: "steady" }[trend.trend as string] ?? "steady";
}

function SectionTitle({ letter, title }: { letter: string; title: string }) {
  return (
    <h2 className="flex items-baseline gap-3 text-2xl">
      <span className="readout text-sm text-ink-faint">{letter}.</span>
      {title}
    </h2>
  );
}

function Section({
  letter,
  title,
  more,
  children,
}: {
  letter: string;
  title: string;
  more?: { href: string; label: string };
  children: React.ReactNode;
}) {
  return (
    <section className="mt-14">
      <div className="mb-4 flex items-end justify-between gap-4">
        <SectionTitle letter={letter} title={title} />
        {more && (
          <Link
            href={more.href}
            className="group inline-flex items-center gap-1 text-sm text-ink-soft transition-colors hover:text-ink"
          >
            {more.label}
            <ArrowUpRight className="h-3.5 w-3.5 transition-transform group-hover:-translate-y-0.5 group-hover:translate-x-0.5" />
          </Link>
        )}
      </div>
      {children}
    </section>
  );
}

function StatusCell({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="bg-surface p-4 sm:p-5">
      <p className="label mb-2.5">{label}</p>
      {children}
    </div>
  );
}

function VerdictLine({ verdict }: { verdict: "ok" | "caution" | "refer" }) {
  const config = {
    ok: { icon: CheckCircle2, tone: "text-ok", text: "No red flags", note: "Nothing needs a clinician right now" },
    caution: { icon: AlertTriangle, tone: "text-caution", text: "Interpret with caution", note: "Read the reasons before acting" },
    refer: { icon: Stethoscope, tone: "text-alert", text: "See a clinician", note: "Self-care suggestions are withheld" },
  }[verdict];
  const Icon = config.icon;
  return (
    <>
      <p className={cn("flex items-center gap-2 text-[0.95rem] font-medium", config.tone)}>
        <Icon className="h-4 w-4 shrink-0" strokeWidth={2} />
        {config.text}
      </p>
      <p className="caption mt-1">{config.note}</p>
    </>
  );
}

/* A measurement mounted like an instrument plate in a ruled tray. */
function Plate({
  label,
  value,
  caption,
  confidence,
  href,
}: {
  label: string;
  value: React.ReactNode;
  caption: string;
  confidence?: number | null;
  href: string;
}) {
  return (
    <Link
      href={href}
      className="group relative flex min-h-[12.5rem] flex-col bg-surface p-5 transition-colors hover:bg-surface-sunken"
    >
      <span
        aria-hidden="true"
        className="absolute inset-y-0 left-0 w-[3px] origin-top scale-y-0 bg-marker transition-transform duration-300 group-hover:scale-y-100"
      />
      <div className="flex items-start justify-between gap-2">
        <span className="label">{label}</span>
        <ArrowUpRight className="h-3.5 w-3.5 text-ink-faint opacity-0 transition-opacity group-hover:opacity-100" />
      </div>
      <div className="mt-5 flex-1">
        <div className="text-ink">{value}</div>
        <p className="mt-2 text-[0.8125rem] leading-snug text-ink-soft">{caption}</p>
      </div>
      {confidence != null && (
        <ConfidenceScale value={confidence} label={label} size="sm" showBand={false} className="mt-4" />
      )}
    </Link>
  );
}

function FirstRun() {
  const steps = [
    { title: "About you", body: "When and where thinning started, in your own words." },
    { title: "Health & habits", body: "Medical, stress and styling factors a photograph cannot see." },
    { title: "Safety screen", body: "Checks for signs that need a clinician before anything else." },
    { title: "Guided capture", body: "Framing guides for each view, so next month compares fairly." },
  ];
  return (
    <div className="animate-rise">
      <PageHeader
        index="Nº 01"
        eyebrow="Overview · no readings yet"
        title={
          <>
            Start your <span className="marker">baseline</span>.
          </>
        }
        dek="Four short steps, about ten minutes. The first capture becomes the reference every later one is measured against."
      />
      <div className="grid gap-10 lg:grid-cols-12">
        <ol className="divide-y divide-rule border-y border-rule lg:col-span-7">
          {steps.map((s, i) => (
            <li key={s.title} className="grid grid-cols-[3rem_1fr] gap-x-4 py-5">
              <span className="readout pt-1 text-sm text-ink-faint">{String(i + 1).padStart(2, "0")}</span>
              <div>
                <p className="font-display text-2xl leading-tight">{s.title}</p>
                <p className="mt-1 text-sm leading-relaxed text-ink-soft">{s.body}</p>
              </div>
            </li>
          ))}
        </ol>
        <div className="lg:col-span-5">
          <div className="crop-marks">
            <div className="graph-paper flex aspect-[4/3] items-center justify-center border border-rule bg-surface">
              <ReticleMark className="h-24 w-24 text-ink-faint" />
            </div>
          </div>
          <p className="caption mt-3">Fig. 1 · Your first plate will be mounted here.</p>
          <div className="mt-6 flex flex-wrap gap-2">
            <Link href="/assessment" className={buttonVariants({ size: "lg" })}>
              Start the assessment
              <ArrowRight className="h-4 w-4" />
            </Link>
            <Link href="/scan/hair" className={buttonVariants({ size: "lg", variant: "outline" })}>
              <Camera className="h-4 w-4" strokeWidth={1.75} />
              Just take a scan
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
