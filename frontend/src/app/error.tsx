"use client";

import React, { useEffect } from "react";
import Link from "next/link";
import { AlertTriangle, RefreshCw, Home } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("[HairGPT Client Error]:", error);
  }, [error]);

  return (
    <div className="mx-auto max-w-lg py-12 px-4 text-center animate-rise">
      <div className="rounded-2xl border border-rule bg-surface p-8 shadow-xs">
        <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-alert-wash text-alert">
          <AlertTriangle className="h-6 w-6" />
        </div>

        <h2 className="text-xl font-bold text-ink">We couldn't load this screen</h2>
        <p className="mt-2 text-sm text-ink-soft leading-relaxed">
          {error.message || "An unexpected error occurred while loading your hair data."}
        </p>

        <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
          <Button
            onClick={() => reset()}
            className="rounded-xl bg-accent text-white hover:bg-accent/90 gap-2"
          >
            <RefreshCw className="h-4 w-4" />
            <span>Try Again</span>
          </Button>

          <Link href="/">
            <Button variant="outline" className="rounded-xl gap-2">
              <Home className="h-4 w-4" />
              <span>Back to Overview</span>
            </Button>
          </Link>
        </div>

        {error.digest && (
          <p className="mt-6 text-[10px] text-ink-faint font-mono">
            Error Digest: {error.digest}
          </p>
        )}
      </div>
    </div>
  );
}
