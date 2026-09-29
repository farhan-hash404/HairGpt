"use client";

import { motion } from "framer-motion";
import * as React from "react";

import { cn } from "@/lib/utils";

const STORAGE_KEY = "hairgpt-theme";
type Theme = "light" | "dark";

function effectiveTheme(): Theme {
  const explicit = document.documentElement.dataset.theme;
  if (explicit === "light" || explicit === "dark") return explicit;
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

const EASE = { ease: "easeInOut", duration: 0.35 } as const;

/* Sun-to-moon toggle adapted from Skiper UI's skiper4 (ThemeToggleButton2).
   The registry copy has its SVG numbers de-duplicated ("0 0 32 32" became
   "0 32", "a1 1 0 0 0 9 13" became "a1 1 0 9 13"); the geometry here is
   restored from each command's argument count. */
export function ThemeToggle({ className }: { className?: string }) {
  const [theme, setTheme] = React.useState<Theme | null>(null);
  const clipId = `theme-cut-${React.useId().replace(/[^a-zA-Z0-9_-]/g, "")}`;

  React.useEffect(() => {
    setTheme(effectiveTheme());
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const follow = () => setTheme(effectiveTheme());
    media.addEventListener("change", follow);
    return () => media.removeEventListener("change", follow);
  }, []);

  const isDark = theme === "dark";

  function toggle() {
    const next: Theme = isDark ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // Private mode: the choice lasts for this page only.
    }
    setTheme(next);
  }

  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={isDark ? "Switch to light theme" : "Switch to dark theme"}
      title={isDark ? "Light theme" : "Dark theme"}
      className={cn(
        "inline-flex h-10 w-10 items-center justify-center rounded text-ink-soft transition-colors hover:bg-surface-sunken hover:text-ink",
        className
      )}
    >
      <svg
        viewBox="0 0 32 32"
        className="h-[18px] w-[18px]"
        fill="currentColor"
        strokeLinecap="round"
        aria-hidden="true"
        style={{ visibility: theme ? "visible" : "hidden" }}
      >
        <clipPath id={clipId}>
          <motion.path
            initial={false}
            animate={{ y: isDark ? 10 : 0, x: isDark ? -12 : 0 }}
            transition={EASE}
            d="M0-5h30a1 1 0 0 0 9 13v24H0Z"
          />
        </clipPath>
        <g clipPath={`url(#${clipId})`}>
          <motion.circle initial={false} animate={{ r: isDark ? 10 : 8 }} transition={EASE} cx="16" cy="16" />
          <motion.g
            initial={false}
            animate={{ rotate: isDark ? -100 : 0, scale: isDark ? 0.5 : 1, opacity: isDark ? 0 : 1 }}
            transition={EASE}
            stroke="currentColor"
            strokeWidth="1.5"
            style={{ transformOrigin: "16px 16px" }}
          >
            <path d="M16 5.5v-4" />
            <path d="M16 30.5v-4" />
            <path d="M1.5 16h4" />
            <path d="M26.5 16h4" />
            <path d="m23.4 8.6 2.8-2.8" />
            <path d="m5.7 26.3 2.9-2.9" />
            <path d="m5.8 5.8 2.8 2.8" />
            <path d="m23.4 23.4 2.9 2.9" />
          </motion.g>
        </g>
      </svg>
    </button>
  );
}
