"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { AlertTriangle, Camera, Check, RefreshCw, Upload } from "lucide-react";
import { api, getToken, type CaptureReference, type QualityReport } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  EMPTY_HAIR,
  EMPTY_SKIN,
  SymptomCheck,
  type HairSymptoms,
  type SkinSymptoms,
} from "@/components/symptom-check";
import { cn, titleize } from "@/lib/utils";

const VIEW_COACHING: Record<string, string> = {
  front_hairline: "Face the camera. Center your hairline in the guide.",
  left_temple: "Turn your head right so the left temple faces the camera.",
  right_temple: "Turn your head left so the right temple faces the camera.",
  top: "Tilt your head down, camera above, showing the top of the scalp.",
  crown: "Camera above and behind, centered on the crown (swirl area).",
  sides: "Side profile, hair visible from ear to crown.",
  back: "Back of the head, camera level and centered.",
  front: "Face the camera squarely, neutral expression, even lighting.",
  left: "Turn your head right to show the left side of your face.",
  right: "Turn your head left to show the right side of your face.",
};

type Captured = Record<string, QualityReport>;

export function GuidedCapture({
  domain,
  /** Symptom answers already collected upstream (the assessment flow asks them
   *  before capture). When provided, the in-component check is skipped so the
   *  user is never asked the same safety questions twice. */
  presetSymptoms,
  onComplete,
}: {
  domain: "hair" | "skin";
  presetSymptoms?: HairSymptoms;
  onComplete?: (sessionId: string) => void;
}) {
  const router = useRouter();
  const [sessionId, setSessionId] = React.useState<string | null>(null);
  const [views, setViews] = React.useState<string[]>([]);
  const [current, setCurrent] = React.useState(0);
  const [captured, setCaptured] = React.useState<Captured>({});
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [analyzing, setAnalyzing] = React.useState(false);

  const videoRef = React.useRef<HTMLVideoElement>(null);
  const streamRef = React.useRef<MediaStream | null>(null);
  const [cameraOn, setCameraOn] = React.useState(false);
  const [hairSymptoms, setHairSymptoms] = React.useState<HairSymptoms>(presetSymptoms ?? EMPTY_HAIR);
  const [skinSymptoms, setSkinSymptoms] = React.useState<SkinSymptoms>(EMPTY_SKIN);
  const symptomsCollectedUpstream = presetSymptoms !== undefined;

  // Ghost overlay: the previous scan's photo for this view, shown translucently
  // so repeat captures are framed the same way. This is the single biggest lever
  // on longitudinal comparability.
  const [reference, setReference] = React.useState<CaptureReference>(null);
  const [ghostUrl, setGhostUrl] = React.useState<string | null>(null);
  const [ghostOn, setGhostOn] = React.useState(true);
  const [ghostOpacity, setGhostOpacity] = React.useState(0.4);

  React.useEffect(() => {
    (async () => {
      try {
        const s = await api.createScan(domain);
        setSessionId(s.session_id);
        setViews(s.required_views);
      } catch (e: any) {
        setError(e?.message ?? "Could not start a scan");
      }
      try {
        const { reference: ref } = await api.captureReference(domain);
        setReference(ref);
      } catch {
        /* no reference scan yet — first-time capture, ghost simply unavailable */
      }
    })();
    return () => stopCamera();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [domain]);

  // Load the ghost image whenever the active view changes.
  const currentView = views[current];
  React.useEffect(() => {
    setGhostUrl(null);
    if (!reference || !currentView || !reference.views.includes(currentView)) return;
    let objectUrl: string | null = null;
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(
          `/api/v1/scans/${reference.session_id}/images/${currentView}/content`,
          { headers: { Authorization: `Bearer ${getToken()}` } }
        );
        if (!res.ok) return;
        const blob = await res.blob();
        if (cancelled) return;
        objectUrl = URL.createObjectURL(blob);
        setGhostUrl(objectUrl);
      } catch {
        /* ghost is a convenience; failing to load it must not block capture */
      }
    })();
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [reference, currentView]);

  async function startCamera() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "user", width: { ideal: 1280 }, height: { ideal: 1280 } },
      });
      streamRef.current = stream;
      if (videoRef.current) videoRef.current.srcObject = stream;
      setCameraOn(true);
    } catch {
      setError("Camera unavailable — you can upload a photo instead.");
    }
  }

  function stopCamera() {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    setCameraOn(false);
  }

  async function submitBlob(blob: Blob) {
    if (!sessionId) return;
    setBusy(true);
    setError(null);
    try {
      const report = await api.uploadImage(sessionId, views[current], blob);
      setCaptured((c) => ({ ...c, [views[current]]: report }));
      // Only advance when the quality gate passes — we never analyze bad images.
      if (report.overall_pass && current < views.length - 1) setCurrent((i) => i + 1);
    } catch (e: any) {
      setError(e?.message ?? "Upload failed");
    } finally {
      setBusy(false);
    }
  }

  async function capture() {
    const video = videoRef.current;
    if (!video) return;
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth || 720;
    canvas.height = video.videoHeight || 720;
    canvas.getContext("2d")?.drawImage(video, 0, 0, canvas.width, canvas.height);
    canvas.toBlob((blob) => blob && submitBlob(blob), "image/jpeg", 0.92);
  }

  async function runAnalysis() {
    if (!sessionId) return;
    setAnalyzing(true);
    setError(null);
    try {
      // Self-reported symptoms feed the deterministic safety engine, which can
      // force a referral for signs the images cannot show.
      await api.analyze(sessionId, {
        hair_symptoms: domain === "hair" ? hairSymptoms : null,
        skin_symptoms: domain === "skin" ? skinSymptoms : null,
      });
      stopCamera();
      if (onComplete) onComplete(sessionId);
      else router.push(`/scan/${sessionId}/result`);
    } catch (e: any) {
      const d = e?.detail;
      setError(
        d?.code === "views_incomplete"
          ? `Still needed: ${(d.missing_or_failed ?? []).map(titleize).join(", ")}`
          : e?.message ?? "Analysis failed"
      );
      setAnalyzing(false);
    }
  }

  const view = views[current];
  const report = view ? captured[view] : undefined;
  const passedCount = Object.values(captured).filter((r) => r.overall_pass).length;
  const allPassed = views.length > 0 && passedCount === views.length;

  return (
    <div className={cn("space-y-5", !onComplete && "mx-auto max-w-3xl")}>
      {/* When embedded in the assessment, the surrounding step supplies the
          heading — repeating it here would double the page title. */}
      {!onComplete && (
        <div>
          <h1 className="text-2xl font-normal">
            {domain === "hair" ? "Guided hair &amp; scalp scan" : "Guided facial scan"}
          </h1>
          <p className="mt-2 max-w-[62ch] text-sm text-ink-soft">
            {views.length} standardized views. Each photo passes an image-quality check before anything is analysed.
          </p>
        </div>
      )}

      {/* View rail */}
      <ol className="flex flex-wrap gap-1.5">
        {views.map((v, i) => {
          const r = captured[v];
          const state = r?.overall_pass ? "pass" : r ? "fail" : i === current ? "current" : "todo";
          return (
            <li key={v}>
              <button
                onClick={() => setCurrent(i)}
                aria-current={state === "current" ? "step" : undefined}
                className={cn(
                  "flex items-center gap-1.5 rounded-sm border px-2.5 py-1.5 font-mono text-[11px] tracking-[0.02em] transition-colors",
                  state === "pass" && "border-ok/40 bg-ok-wash text-ok",
                  state === "fail" && "border-alert/40 bg-alert-wash text-alert",
                  state === "current" && "border-ink bg-surface font-medium text-ink shadow-[inset_0_-3px_0_hsl(var(--marker))]",
                  state === "todo" && "border-rule text-ink-faint hover:border-rule-strong hover:text-ink-soft"
                )}
              >
                <span className="opacity-60">{String(i + 1).padStart(2, "0")}</span>
                {state === "pass" && <Check className="h-3 w-3" aria-hidden="true" />}
                {state === "fail" && <AlertTriangle className="h-3 w-3" aria-hidden="true" />}
                {titleize(v)}
              </button>
            </li>
          );
        })}
      </ol>

      {/* Camera / capture surface: a viewfinder with registration corners. */}
      <Card className="overflow-hidden">
        <div className="relative aspect-square w-full bg-black/90 sm:aspect-[4/3]">
          <div
            aria-hidden="true"
            className="pointer-events-none absolute inset-4 z-10 [--crop:rgba(255,255,255,0.75)] [--crop-len:22px] crop-marks"
          />
          <video ref={videoRef} autoPlay playsInline muted className="h-full w-full object-cover" />

          {/* Ghost of the previous scan's same view — match this and the two
              photos stay comparable. */}
          {ghostOn && ghostUrl && (
            <img
              src={ghostUrl}
              alt=""
              aria-hidden="true"
              className="pointer-events-none absolute inset-0 h-full w-full object-cover mix-blend-luminosity"
              style={{ opacity: ghostOpacity }}
            />
          )}

          {/* Silhouette guide */}
          <div className="pointer-events-none absolute inset-0 grid place-items-center">
            <div className="h-[70%] w-[55%] rounded-[45%] border-2 border-dashed border-white/60" />
          </div>

          {ghostUrl && ghostOn && (
            <p className="readout absolute left-3 top-3 rounded bg-black/65 px-2 py-1 text-2xs uppercase tracking-wider text-white">
              Ghost · last scan
            </p>
          )}
          <div className="pointer-events-none absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/75 to-transparent p-4">
            <p className="font-display text-base text-white">{titleize(view ?? "")}</p>
            <p className="mt-0.5 max-w-[46ch] text-xs text-white/85">
              {VIEW_COACHING[view] ?? "Center the region in the guide."}
            </p>
          </div>
          {!cameraOn && (
            <div className="absolute inset-0 grid place-items-center bg-surface/97">
              <div className="text-center">
                <Button onClick={startCamera}>
                  <Camera className="h-4 w-4" /> Enable camera
                </Button>
                <p className="mt-3 text-xs text-ink-faint">or upload a photo below</p>
              </div>
            </div>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-2 border-t p-4">
          <Button onClick={capture} disabled={!cameraOn || busy}>
            <Camera className="h-4 w-4" /> {busy ? "Checking quality…" : "Capture"}
          </Button>
          <label className="inline-flex">
            <input
              type="file"
              accept="image/*"
              className="sr-only"
              onChange={(e) => e.target.files?.[0] && submitBlob(e.target.files[0])}
            />
            <span className={cn(buttonVariants({ variant: "outline" }), "cursor-pointer")}>
              <Upload className="h-4 w-4" /> Upload photo
            </span>
          </label>
          {report && !report.overall_pass && (
            <Button variant="ghost" onClick={() => setCaptured((c) => ({ ...c, [view]: undefined as any }))}>
              <RefreshCw className="h-4 w-4" /> Retake
            </Button>
          )}
        </div>

        {ghostUrl && (
          <div className="flex flex-wrap items-center gap-x-5 gap-y-2 border-t bg-surface-sunken px-4 py-3 text-sm">
            <label className="flex cursor-pointer items-center gap-2">
              <input
                type="checkbox"
                checked={ghostOn}
                onChange={(e) => setGhostOn(e.target.checked)}
                className="h-4 w-4 accent-[hsl(var(--ink))]"
              />
              <span className="font-medium">Show last scan as a guide</span>
            </label>
            {ghostOn && (
              <label className="flex items-center gap-2">
                <span className="label">Opacity</span>
                <input
                  type="range"
                  min={0.1}
                  max={0.8}
                  step={0.05}
                  value={ghostOpacity}
                  onChange={(e) => setGhostOpacity(Number(e.target.value))}
                  className="w-28 accent-[hsl(var(--ink))]"
                  aria-label="Ghost overlay opacity"
                />
              </label>
            )}
            <span className="text-xs text-ink-faint">Matching it keeps your scans comparable.</span>
          </div>
        )}
      </Card>

      {/* Quality feedback — the gate that blocks analysis */}
      {report && <QualityPanel report={report} />}
      {error && <p className="text-sm text-alert">{error}</p>}

      {/* Safety check — shown once every view has passed, just before analysis.
          Skipped when the assessment flow already asked these questions. */}
      {allPassed && !symptomsCollectedUpstream && (
        <SymptomCheck
          domain={domain}
          hair={hairSymptoms}
          skin={skinSymptoms}
          onHairChange={setHairSymptoms}
          onSkinChange={setSkinSymptoms}
        />
      )}

      <div className="flex flex-wrap items-center justify-between gap-4 border-t border-ink pt-4">
        <div className="min-w-[12rem] flex-1">
          <p className="text-sm text-ink-soft">
            <span className="readout font-medium text-ink">
              {passedCount}/{views.length}
            </span>{" "}
            views passed quality
          </p>
          <div className="mt-2 flex max-w-xs gap-1" aria-hidden="true">
            {views.map((v) => (
              <span key={v} className={cn("h-[3px] flex-1", captured[v]?.overall_pass ? "bg-ink" : "bg-rule")} />
            ))}
          </div>
        </div>
        <Button onClick={runAnalysis} disabled={!allPassed || analyzing}>
          {analyzing ? "Analysing…" : "Analyse scan"}
        </Button>
      </div>
    </div>
  );
}

function QualityPanel({ report }: { report: QualityReport }) {
  return (
    <div className="panel flex overflow-hidden">
      {/* Severity stripe: pass/fail reads before any of the numbers do. */}
      <span className={cn("w-1 shrink-0", report.overall_pass ? "bg-ok" : "bg-alert")} aria-hidden="true" />
      <div className="min-w-0 flex-1 p-4">
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <Badge variant={report.overall_pass ? "ok" : "alert"}>
            {report.overall_pass ? "Quality passed" : "Failed — not analysed"}
          </Badge>
          {report.is_mock && <Badge variant="flag">heuristic gate</Badge>}
          <span className="readout text-2xs text-ink-faint">
            gate confidence {Math.round(report.confidence.value * 100)}%
          </span>
        </div>

        <dl className="grid grid-cols-2 gap-x-6 gap-y-3 sm:grid-cols-3">
          <Stat label="Sharpness" value={report.blur_score} />
          <Stat label="Exposure" value={report.exposure_score} />
          <Stat label="Overexposed" value={report.overexposed_frac} invert />
          <Stat label="Distance" ok={report.distance_ok} />
          <Stat label="Angle" ok={report.angle_ok} />
          {report.scalp_visibility !== null && <Stat label="Scalp visible" value={report.scalp_visibility} />}
          {/* Framing warns, never blocks — see the note below. */}
          {report.framing_match !== null && (
            <Stat label="Matches last scan" value={report.framing_match} threshold={0.6} />
          )}
        </dl>

        {report.framing_match !== null && report.framing_match < 0.6 && (
          <p className="mt-4 border-l-2 border-caution bg-caution-wash p-3 text-sm">
            Framed differently from your last scan. This won&apos;t stop the analysis, but it lowers the confidence of
            any before/after comparison.
          </p>
        )}

        {!!report.retake_guidance.length && (
          <div className="mt-4 border-t pt-3">
            <p className="label mb-2">How to fix it</p>
            <ul className="space-y-1 text-sm text-ink-soft">
              {report.retake_guidance.map((g, i) => (
                <li key={i} className="flex gap-2">
                  <span aria-hidden="true" className="text-ink-faint">
                    —
                  </span>
                  <span>{g}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}

function Stat({
  label,
  value,
  ok,
  invert,
  threshold,
}: {
  label: string;
  value?: number;
  ok?: boolean;
  invert?: boolean;
  threshold?: number;
}) {
  const good =
    ok !== undefined ? ok : invert ? (value ?? 0) < 0.12 : (value ?? 0) > (threshold ?? 0.35);
  return (
    <div>
      <dt className="label">{label}</dt>
      <dd className={cn("readout mt-0.5 text-sm font-medium", good ? "text-ink" : "text-alert")}>
        {ok !== undefined ? (ok ? "OK" : "Off") : `${Math.round((value ?? 0) * 100)}%`}
      </dd>
    </div>
  );
}
