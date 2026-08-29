"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { AlertTriangle, Camera, Check, RefreshCw, Upload } from "lucide-react";
import { api, type QualityReport } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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

export function GuidedCapture({ domain }: { domain: "hair" | "skin" }) {
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
  const [hairSymptoms, setHairSymptoms] = React.useState<HairSymptoms>(EMPTY_HAIR);
  const [skinSymptoms, setSkinSymptoms] = React.useState<SkinSymptoms>(EMPTY_SKIN);

  React.useEffect(() => {
    (async () => {
      try {
        const s = await api.createScan(domain);
        setSessionId(s.session_id);
        setViews(s.required_views);
      } catch (e: any) {
        setError(e?.message ?? "Could not start a scan");
      }
    })();
    return () => stopCamera();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [domain]);

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
      router.push(`/scan/${sessionId}/result`);
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
    <div className="mx-auto max-w-3xl space-y-5">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">
          {domain === "hair" ? "Guided hair & scalp scan" : "Guided facial scan"}
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          {views.length} standardized views. Each photo passes an image-quality check before anything is analyzed.
        </p>
      </div>

      {/* Progress rail */}
      <div className="flex flex-wrap gap-2">
        {views.map((v, i) => {
          const r = captured[v];
          const state = r?.overall_pass ? "pass" : r ? "fail" : i === current ? "current" : "todo";
          return (
            <button
              key={v}
              onClick={() => setCurrent(i)}
              className={cn(
                "flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs transition-colors",
                state === "pass" && "border-primary/40 bg-primary/10 text-primary",
                state === "fail" && "border-destructive/40 bg-destructive/10 text-destructive",
                state === "current" && "border-foreground/30 bg-muted font-medium",
                state === "todo" && "text-muted-foreground"
              )}
            >
              {state === "pass" && <Check className="h-3 w-3" />}
              {state === "fail" && <AlertTriangle className="h-3 w-3" />}
              {titleize(v)}
            </button>
          );
        })}
      </div>

      {/* Camera / capture surface */}
      <Card className="overflow-hidden">
        <div className="relative aspect-square w-full bg-black/90 sm:aspect-[4/3]">
          <video ref={videoRef} autoPlay playsInline muted className="h-full w-full object-cover" />
          {/* Silhouette guide */}
          <div className="pointer-events-none absolute inset-0 grid place-items-center">
            <div className="h-[70%] w-[55%] rounded-[45%] border-2 border-dashed border-white/60" />
          </div>
          <div className="pointer-events-none absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/70 to-transparent p-4">
            <p className="text-sm font-medium text-white">{titleize(view ?? "")}</p>
            <p className="text-xs text-white/80">{VIEW_COACHING[view] ?? "Center the region in the guide."}</p>
          </div>
          {!cameraOn && (
            <div className="absolute inset-0 grid place-items-center bg-background/95">
              <div className="text-center">
                <Button onClick={startCamera}>
                  <Camera className="h-4 w-4" /> Enable camera
                </Button>
                <p className="mt-3 text-xs text-muted-foreground">or upload a photo below</p>
              </div>
            </div>
          )}
        </div>

        <CardContent className="flex flex-wrap items-center gap-3 pt-5">
          <Button onClick={capture} disabled={!cameraOn || busy}>
            <Camera className="h-4 w-4" /> {busy ? "Checking quality…" : "Capture"}
          </Button>
          <label className="inline-flex">
            <input
              type="file"
              accept="image/*"
              className="hidden"
              onChange={(e) => e.target.files?.[0] && submitBlob(e.target.files[0])}
            />
            <span className="inline-flex h-10 cursor-pointer items-center gap-2 rounded-full border px-5 text-sm hover:bg-muted">
              <Upload className="h-4 w-4" /> Upload photo
            </span>
          </label>
          {report && !report.overall_pass && (
            <Button variant="ghost" onClick={() => setCaptured((c) => ({ ...c, [view]: undefined as any }))}>
              <RefreshCw className="h-4 w-4" /> Retake
            </Button>
          )}
        </CardContent>
      </Card>

      {/* Quality feedback — the gate that blocks analysis */}
      {report && <QualityPanel report={report} />}
      {error && <p className="text-sm text-destructive">{error}</p>}

      {/* Safety check — shown once every view has passed, just before analysis. */}
      {allPassed && (
        <SymptomCheck
          domain={domain}
          hair={hairSymptoms}
          skin={skinSymptoms}
          onHairChange={setHairSymptoms}
          onSkinChange={setSkinSymptoms}
        />
      )}

      <div className="flex items-center justify-between gap-4 rounded-[var(--radius)] border bg-muted/40 p-4">
        <p className="text-sm">
          <span className="font-medium">{passedCount}</span> of {views.length} views passed quality
        </p>
        <Button onClick={runAnalysis} disabled={!allPassed || analyzing}>
          {analyzing ? "Analyzing…" : "Analyze scan"}
        </Button>
      </div>
    </div>
  );
}

function QualityPanel({ report }: { report: QualityReport }) {
  return (
    <Card className={cn("border-2", report.overall_pass ? "border-primary/30" : "border-destructive/40")}>
      <CardContent className="pt-5">
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <Badge variant={report.overall_pass ? "default" : "destructive"}>
            {report.overall_pass ? "Quality passed" : "Quality failed — not analyzed"}
          </Badge>
          {report.is_mock && <Badge variant="mock">heuristic gate</Badge>}
          <span className="text-xs text-muted-foreground">
            gate confidence {Math.round(report.confidence.value * 100)}%
          </span>
        </div>

        <dl className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-3">
          <Stat label="Sharpness" value={report.blur_score} />
          <Stat label="Exposure" value={report.exposure_score} />
          <Stat label="Overexposed" value={report.overexposed_frac} invert />
          <Stat label="Distance" ok={report.distance_ok} />
          <Stat label="Angle" ok={report.angle_ok} />
          {report.scalp_visibility !== null && <Stat label="Scalp visible" value={report.scalp_visibility} />}
        </dl>

        {!!report.retake_guidance.length && (
          <div className="mt-4 rounded-xl bg-muted/60 p-3">
            <p className="mb-1 text-sm font-medium">How to fix it</p>
            <ul className="ml-4 list-disc text-sm text-muted-foreground">
              {report.retake_guidance.map((g, i) => (
                <li key={i}>{g}</li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function Stat({ label, value, ok, invert }: { label: string; value?: number; ok?: boolean; invert?: boolean }) {
  const good = ok !== undefined ? ok : invert ? (value ?? 0) < 0.12 : (value ?? 0) > 0.35;
  return (
    <div>
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className={cn("font-medium tabular-nums", good ? "text-foreground" : "text-destructive")}>
        {ok !== undefined ? (ok ? "OK" : "Off") : `${Math.round((value ?? 0) * 100)}%`}
      </dd>
    </div>
  );
}
