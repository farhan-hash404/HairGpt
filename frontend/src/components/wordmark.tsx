import Link from "next/link";

import { cn } from "@/lib/utils";

/* A microscope reticle over a hair shaft in cross-section: what HairGPT does
   (measure a hair) drawn the way an instrument would draw it. */
export function ReticleMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={className} aria-hidden="true" fill="none">
      <circle cx="16" cy="16" r="9.25" stroke="currentColor" strokeWidth="1.5" />
      <circle cx="16" cy="16" r="3.4" className="fill-accent" />
      <path d="M16 1.75v4.5M16 25.75v4.5M1.75 16h4.5M25.75 16h4.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

export function Wordmark({ className }: { className?: string }) {
  return (
    <Link href="/" className={cn("group flex items-center gap-2.5", className)} aria-label="HairGPT home">
      <ReticleMark className="h-7 w-7 text-ink transition-transform duration-500 ease-out group-hover:rotate-90" />
      <span className="flex items-baseline gap-[3px]">
        <span className="font-display text-[1.5rem] leading-none tracking-[-0.02em] text-ink">Hair</span>
        <span className="font-mono text-[0.68rem] font-medium uppercase tracking-[0.16em] text-accent">GPT</span>
      </span>
    </Link>
  );
}
