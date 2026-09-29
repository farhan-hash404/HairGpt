"use client";

import NumberFlow from "@number-flow/react";
import { useInView } from "react-intersection-observer";

import { cn } from "@/lib/utils";

/* A measurement that counts up from zero the first time it scrolls into view.
   The pattern of Skiper UI's animated number (skiper37), built on NumberFlow;
   NumberFlow honours prefers-reduced-motion and keeps the digits accessible. */
export function Readout({
  value,
  digits = 0,
  prefix,
  suffix,
  className,
}: {
  value: number | null | undefined;
  digits?: number;
  prefix?: string;
  suffix?: string;
  className?: string;
}) {
  const { ref, inView } = useInView({ triggerOnce: true, threshold: 0.3 });

  if (value === null || value === undefined || Number.isNaN(value)) {
    return <span className={cn("readout", className)}>—</span>;
  }

  return (
    <span ref={ref} className={cn("readout", className)}>
      <NumberFlow
        value={inView ? value : 0}
        format={{ minimumFractionDigits: digits, maximumFractionDigits: digits }}
        prefix={prefix}
        suffix={suffix}
      />
    </span>
  );
}

/** A 0–1 fraction shown as a percentage readout. */
export function PercentReadout({ value, digits = 0, className }: { value: number | null | undefined; digits?: number; className?: string }) {
  return (
    <Readout
      value={value === null || value === undefined ? value : value * 100}
      digits={digits}
      suffix="%"
      className={className}
    />
  );
}
