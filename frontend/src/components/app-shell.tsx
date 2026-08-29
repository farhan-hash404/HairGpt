"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

/* Primary nav stays short enough never to wrap; the rest sits behind "More",
   so adding a feature doesn't degrade the header. */
const NAV = [
  { href: "/", label: "Overview" },
  { href: "/assessment", label: "Assessment" },
  { href: "/shedding", label: "Shedding" },
  { href: "/timeline", label: "Timeline" },
  { href: "/compare", label: "Compare" },
];

const MORE_NAV = [
  { href: "/history", label: "Your history" },
  { href: "/treatments", label: "Treatments" },
  { href: "/products", label: "Products" },
  { href: "/settings", label: "Settings & privacy" },
];

function isActive(pathname: string, href: string) {
  return href === "/" ? pathname === "/" : pathname.startsWith(href);
}

/** The wordmark doubles as the product's thesis: a measured reading, not a verdict. */
function Wordmark() {
  return (
    <Link href="/" className="group flex items-baseline gap-2" aria-label="HairGPT home">
      <span className="font-display text-xl font-semibold tracking-tight">HairGPT</span>
      <span className="hidden select-none text-2xs uppercase tracking-[0.14em] text-ink-faint sm:inline">
        observation, not diagnosis
      </span>
    </Link>
  );
}

function MoreMenu({ pathname }: { pathname: string }) {
  const [open, setOpen] = React.useState(false);
  const ref = React.useRef<HTMLDivElement>(null);
  const active = MORE_NAV.some((item) => pathname.startsWith(item.href));

  React.useEffect(() => {
    if (!open) return;
    const onPointerDown = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    const onKeyDown = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-haspopup="menu"
        className={cn(
          "flex items-center gap-1 rounded px-2.5 py-1.5 text-sm transition-colors",
          active ? "text-ink" : "text-ink-soft hover:text-ink"
        )}
      >
        More
        <ChevronDown className={cn("h-3.5 w-3.5 transition-transform", open && "rotate-180")} />
      </button>
      {open && (
        <div
          role="menu"
          className="panel absolute right-0 top-full z-50 mt-1.5 w-56 overflow-hidden p-1 shadow-lg"
        >
          {MORE_NAV.map(({ href, label }) => (
            <Link
              key={href}
              href={href}
              role="menuitem"
              onClick={() => setOpen(false)}
              className={cn(
                "block rounded px-2.5 py-2 text-sm transition-colors",
                pathname.startsWith(href)
                  ? "bg-accent-wash text-accent"
                  : "text-ink-soft hover:bg-surface-sunken hover:text-ink"
              )}
            >
              {label}
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-40 border-b bg-ground/85 backdrop-blur-md">
        <div className="container flex h-14 items-center justify-between gap-6">
          <Wordmark />

          <nav className="hidden items-center gap-0.5 md:flex" aria-label="Primary">
            {NAV.map(({ href, label }) => {
              const active = isActive(pathname, href);
              return (
                <Link
                  key={href}
                  href={href}
                  aria-current={active ? "page" : undefined}
                  className={cn(
                    "relative rounded px-2.5 py-1.5 text-sm transition-colors",
                    active ? "text-ink" : "text-ink-soft hover:text-ink"
                  )}
                >
                  {label}
                  {/* The active marker is a rule, matching the calibration
                      language used throughout the product. */}
                  {active && (
                    <span className="absolute inset-x-2.5 -bottom-[13px] h-px bg-accent" aria-hidden="true" />
                  )}
                </Link>
              );
            })}
            <MoreMenu pathname={pathname} />
          </nav>
        </div>
      </header>

      <main className="container flex-1 py-10">{children}</main>

      {/* Mobile nav */}
      <nav
        className="sticky bottom-0 z-40 grid grid-cols-5 border-t bg-ground/95 backdrop-blur md:hidden"
        aria-label="Primary mobile"
      >
        {NAV.map(({ href, label }) => {
          const active = isActive(pathname, href);
          return (
            <Link
              key={href}
              href={href}
              aria-current={active ? "page" : undefined}
              className={cn(
                "border-t-2 py-2.5 text-center text-2xs font-medium",
                active ? "border-accent text-ink" : "border-transparent text-ink-faint"
              )}
            >
              {label}
            </Link>
          );
        })}
      </nav>

      <footer className="border-t bg-surface-sunken">
        <div className="container flex flex-col gap-2 py-6 text-xs text-ink-faint">
          <p className="max-w-[68ch]">
            HairGPT produces image-based observations and AI inferences —{" "}
            <strong className="font-semibold text-ink-soft">not a medical diagnosis</strong>. It never prescribes
            medication. The computer-vision models in this build are unvalidated heuristics.
          </p>
          <p>Always consult a qualified clinician for diagnosis and treatment.</p>
        </div>
      </footer>
    </div>
  );
}
