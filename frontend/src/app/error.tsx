"use client";

import React, { useEffect } from "react";
import Link from "next/link";
import { Home, RefreshCw } from "lucide-react";
import { Button, buttonVariants } from "@/components/ui/button";
import { ReticleMark } from "@/components/wordmark";

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
    <div className="mx-auto max-w-xl animate-rise py-10">
      <div className="crop-marks">
        <div className="graph-paper border border-rule bg-surface px-6 py-12 text-center sm:px-10">
          <ReticleMark className="mx-auto h-12 w-12 text-alert" />
          <p className="label mt-5">Something went wrong</p>
          <h1 className="mt-2 text-3xl">We couldn&apos;t load this screen.</h1>
          <p className="mx-auto mt-3 max-w-[48ch] text-sm leading-relaxed text-ink-soft">
            {error.message || "An unexpected error occurred while loading your record."}
          </p>

          <div className="mt-7 flex flex-wrap items-center justify-center gap-2">
            <Button onClick={() => reset()}>
              <RefreshCw className="h-4 w-4" />
              Try again
            </Button>
            <Link href="/" className={buttonVariants({ variant: "outline" })}>
              <Home className="h-4 w-4" />
              Back to overview
            </Link>
          </div>

          {error.digest && <p className="caption mt-6">Error digest: {error.digest}</p>}
        </div>
      </div>
    </div>
  );
}
