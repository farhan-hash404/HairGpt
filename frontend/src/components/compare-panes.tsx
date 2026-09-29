"use client";

import * as React from "react";
import { motion } from "framer-motion";
import { getToken } from "@/lib/api";
import { cn, titleize } from "@/lib/utils";

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

function Placeholder({ label }: { label: string }) {
  return <div className="graph-paper grid h-full place-items-center font-mono text-[11px] text-ink-faint">{label}</div>;
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

type Pane = { id: string; label: string; caption?: string; content: React.ReactNode };

/* The four plates widen on hover or focus: Skiper UI's hover-expand (skiper52)
   motion, adapted to hold any content rather than only image URLs. */
function ExpandStrip({ panes }: { panes: Pane[] }) {
  const [active, setActive] = React.useState(0);
  return (
    <div className="hidden h-[23rem] gap-2 md:flex">
      {panes.map((p, i) => (
        <motion.figure
          key={p.id}
          tabIndex={0}
          aria-label={p.label}
          onHoverStart={() => setActive(i)}
          onFocus={() => setActive(i)}
          initial={false}
          animate={{ flexGrow: active === i ? 2.6 : 1 }}
          transition={{ duration: 0.35, ease: "easeInOut" }}
          style={{ flexBasis: 0 }}
          className="relative min-w-0 cursor-pointer overflow-hidden border border-rule bg-surface-sunken outline-offset-2"
        >
          <div className="absolute inset-0">{p.content}</div>
          <figcaption className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/70 via-black/30 to-transparent px-3 pb-2.5 pt-8 text-white">
            <p className="font-mono text-[11px] uppercase tracking-[0.12em]">
              <span className="text-white/60">{String(i + 1).padStart(2, "0")} </span>
              {p.label}
            </p>
            {p.caption && (
              <p className={cn("mt-0.5 truncate text-[11px] text-white/75 transition-opacity", active === i ? "opacity-100" : "opacity-0")}>
                {p.caption}
              </p>
            )}
          </figcaption>
        </motion.figure>
      ))}
    </div>
  );
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

  const panes: Pane[] = [
    {
      id: "before",
      label: "Before",
      content: before.url ? (
        <img src={before.url} alt="Before scan" className="h-full w-full object-cover" />
      ) : (
        <Placeholder label={before.failed ? "image unavailable" : "loading…"} />
      ),
    },
    {
      id: "after",
      label: "After",
      content: after.url ? (
        <img src={after.url} alt="After scan" className="h-full w-full object-cover" />
      ) : (
        <Placeholder label={after.failed ? "image unavailable" : "loading…"} />
      ),
    },
    {
      id: "overlay",
      label: "Aligned overlay",
      caption: `alignment quality ${Math.round(alignmentQuality * 100)}%`,
      content: ready ? (
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
      ),
    },
    {
      id: "difference",
      label: "Difference",
      caption: "teal = lighter after · amber = darker after",
      content: ready ? <DifferenceCanvas beforeUrl={before.url!} afterUrl={after.url!} /> : <Placeholder label="loading…" />,
    },
  ];

  return (
    <div className="space-y-3">
      {view && (
        <p className="label">
          <span className="text-ink">{titleize(view)} view</span> · the same view is used for both scans
        </p>
      )}

      <div className="crop-marks">
        <ExpandStrip panes={panes} />
        <div className="grid grid-cols-2 gap-2 md:hidden">
          {panes.map((p, i) => (
            <figure key={p.id}>
              <div className="relative aspect-square overflow-hidden border border-rule bg-surface-sunken">{p.content}</div>
              <figcaption className="caption mt-1.5">
                {String(i + 1).padStart(2, "0")} · {p.label}
                {p.caption ? ` · ${p.caption}` : ""}
              </figcaption>
            </figure>
          ))}
        </div>
      </div>

      {ready && (
        <label className="flex flex-wrap items-center gap-3 pt-1 text-sm">
          <span className="label">Overlay blend</span>
          <input
            type="range"
            min={0}
            max={1}
            step={0.01}
            value={overlayOpacity}
            onChange={(e) => setOverlayOpacity(Number(e.target.value))}
            className="w-56 accent-[hsl(var(--ink))]"
            aria-label="Blend between before and after"
          />
          <span className="readout text-xs text-ink-soft">
            {Math.round((1 - overlayOpacity) * 100)}% before / {Math.round(overlayOpacity * 100)}% after
          </span>
        </label>
      )}

      <p className="caption max-w-[80ch]">
        The difference map shows where the two photos differ. Lighting, pose and camera changes also produce
        differences: it is a visual aid, not a measurement, and it cannot show that a treatment worked.
      </p>
    </div>
  );
}
