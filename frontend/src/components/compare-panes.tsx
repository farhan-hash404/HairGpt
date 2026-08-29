"use client";

import * as React from "react";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { getToken } from "@/lib/api";
import { titleize } from "@/lib/utils";

/** Fetch a protected image as an object URL (the API needs a bearer token, so a
 *  plain <img src> cannot be used). */
function useAuthedImage(sessionId: string | null, view: string | null) {
  const [url, setUrl] = React.useState<string | null>(null);
  const [failed, setFailed] = React.useState(false);

  React.useEffect(() => {
    if (!sessionId || !view) return;
    let revoked: string | null = null;
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(`/api/v1/scans/${sessionId}/images/${view}/content`, {
          headers: { Authorization: `Bearer ${getToken()}` },
        });
        if (!res.ok) throw new Error(String(res.status));
        const blob = await res.blob();
        if (cancelled) return;
        revoked = URL.createObjectURL(blob);
        setUrl(revoked);
      } catch {
        if (!cancelled) setFailed(true);
      }
    })();
    return () => {
      cancelled = true;
      if (revoked) URL.revokeObjectURL(revoked);
    };
  }, [sessionId, view]);

  return { url, failed };
}

function Pane({
  title,
  caption,
  children,
}: {
  title: string;
  caption?: string;
  children: React.ReactNode;
}) {
  return (
    <Card className="overflow-hidden">
      <div className="relative aspect-square bg-surface-sunken">{children}</div>
      <div className="p-3">
        <p className="text-sm font-medium">{title}</p>
        {caption && <p className="mt-0.5 text-[11px] text-ink-soft">{caption}</p>}
      </div>
    </Card>
  );
}

function Placeholder({ label }: { label: string }) {
  return <div className="grid h-full place-items-center text-xs text-ink-soft">{label}</div>;
}

/**
 * Difference visualization: per-pixel absolute luminance difference of the two
 * aligned frames, amplified for visibility and tinted.
 *
 * IMPORTANT: this is a *visual aid*, not a measurement. Lighting and pose changes
 * produce difference signal too, which is why the caption says so explicitly.
 */
function DifferenceCanvas({ beforeUrl, afterUrl }: { beforeUrl: string; afterUrl: string }) {
  const ref = React.useRef<HTMLCanvasElement>(null);

  React.useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d", { willReadFrequently: true });
    if (!ctx) return;

    const load = (src: string) =>
      new Promise<HTMLImageElement>((resolve, reject) => {
        const img = new Image();
        img.onload = () => resolve(img);
        img.onerror = reject;
        img.src = src;
      });

    let cancelled = false;
    (async () => {
      try {
        const [b, a] = await Promise.all([load(beforeUrl), load(afterUrl)]);
        if (cancelled) return;
        const S = 320;
        canvas.width = S;
        canvas.height = S;

        const scratch = document.createElement("canvas");
        scratch.width = S;
        scratch.height = S;
        const sctx = scratch.getContext("2d", { willReadFrequently: true });
        if (!sctx) return;

        sctx.drawImage(b, 0, 0, S, S);
        const bd = sctx.getImageData(0, 0, S, S).data;
        sctx.clearRect(0, 0, S, S);
        sctx.drawImage(a, 0, 0, S, S);
        const ad = sctx.getImageData(0, 0, S, S).data;

        const out = ctx.createImageData(S, S);
        for (let i = 0; i < bd.length; i += 4) {
          const lb = 0.299 * bd[i] + 0.587 * bd[i + 1] + 0.114 * bd[i + 2];
          const la = 0.299 * ad[i] + 0.587 * ad[i + 1] + 0.114 * ad[i + 2];
          const diff = Math.min(255, Math.abs(la - lb) * 3); // amplified for visibility
          // Teal where "after" is lighter (more scalp showing), amber where darker.
          const lighter = la > lb;
          out.data[i] = lighter ? diff * 0.2 : diff;
          out.data[i + 1] = lighter ? diff : diff * 0.65;
          out.data[i + 2] = lighter ? diff * 0.85 : diff * 0.1;
          out.data[i + 3] = 255;
        }
        ctx.putImageData(out, 0, 0);
      } catch {
        /* leave canvas blank on failure */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [beforeUrl, afterUrl]);

  return <canvas ref={ref} className="h-full w-full object-cover" aria-label="Difference visualization" />;
}

export function ComparePanes({
  sessionBefore,
  sessionAfter,
  view,
  alignmentQuality,
}: {
  sessionBefore: string;
  sessionAfter: string;
  view: string | null;
  alignmentQuality: number;
}) {
  const before = useAuthedImage(sessionBefore, view);
  const after = useAuthedImage(sessionAfter, view);
  const [overlayOpacity, setOverlayOpacity] = React.useState(0.5);

  const ready = before.url && after.url;

  return (
    <div className="space-y-3">
      {view && (
        <div className="flex flex-wrap items-center gap-2 text-sm text-ink-soft">
          <Badge variant="neutral">{titleize(view)} view</Badge>
          <span>the same view is used for both scans</span>
        </div>
      )}

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Pane title="Before">
          {before.url ? (
            <img src={before.url} alt="Before scan" className="h-full w-full object-cover" />
          ) : (
            <Placeholder label={before.failed ? "image unavailable" : "loading…"} />
          )}
        </Pane>

        <Pane title="After">
          {after.url ? (
            <img src={after.url} alt="After scan" className="h-full w-full object-cover" />
          ) : (
            <Placeholder label={after.failed ? "image unavailable" : "loading…"} />
          )}
        </Pane>

        <Pane title="Aligned overlay" caption={`alignment quality ${Math.round(alignmentQuality * 100)}%`}>
          {ready ? (
            <>
              <img src={before.url!} alt="" className="absolute inset-0 h-full w-full object-cover" />
              <img
                src={after.url!}
                alt="Aligned overlay of both scans"
                className="absolute inset-0 h-full w-full object-cover"
                style={{ opacity: overlayOpacity }}
              />
            </>
          ) : (
            <Placeholder label="loading…" />
          )}
        </Pane>

        <Pane title="Difference" caption="teal = lighter after · amber = darker after">
          {ready ? (
            <DifferenceCanvas beforeUrl={before.url!} afterUrl={after.url!} />
          ) : (
            <Placeholder label="loading…" />
          )}
        </Pane>
      </div>

      {ready && (
        <label className="flex flex-wrap items-center gap-3 text-sm">
          <span className="font-medium">Overlay blend</span>
          <input
            type="range"
            min={0}
            max={1}
            step={0.01}
            value={overlayOpacity}
            onChange={(e) => setOverlayOpacity(Number(e.target.value))}
            className="w-56 accent-[hsl(var(--accent))]"
            aria-label="Blend between before and after"
          />
          <span className="tabular-nums text-ink-soft">
            {Math.round((1 - overlayOpacity) * 100)}% before / {Math.round(overlayOpacity * 100)}% after
          </span>
        </label>
      )}

      <p className="text-[11px] text-ink-soft">
        The difference map highlights where the two photos differ. Lighting, pose and camera changes also produce
        differences — it is a visual aid, not a measurement, and it cannot show that a treatment worked.
      </p>
    </div>
  );
}
