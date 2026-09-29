"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  Calendar,
  ChevronDown,
  ClipboardCheck,
  History,
  Layers,
  LayoutDashboard,
  Pill,
  Plus,
  Settings,
  ShoppingBag,
} from "lucide-react";

import { buttonVariants } from "@/components/ui/button";
import { ProgressiveBlur } from "@/components/ui/skiper-ui/skiper41";
import { Link001 } from "@/components/ui/skiper-ui/skiper40";
import { TextRoll } from "@/components/ui/skiper-ui/skiper58";
import { ThemeToggle } from "@/components/theme-toggle";
import { Wordmark } from "@/components/wordmark";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/assessment", label: "Assessment", icon: ClipboardCheck },
  { href: "/shedding", label: "Shedding", icon: Activity },
  { href: "/timeline", label: "Timeline", icon: Calendar },
  { href: "/compare", label: "Compare", icon: Layers },
];

const MORE_NAV = [
  { href: "/history", label: "Your history", icon: History },
  { href: "/treatments", label: "Treatments & regimen", icon: Pill },
  { href: "/products", label: "Products & ingredients", icon: ShoppingBag },
  { href: "/settings", label: "Settings & privacy", icon: Settings },
];

function isActive(pathname: string, href: string) {
  return href === "/" ? pathname === "/" : pathname.startsWith(href);
}

/* Active page: ink label on a highlighter stroke. Others roll their letters
   on hover (Skiper UI text roll). The rolled copy is decorative, so the
   accessible name comes from a visually hidden label. */
function NavLink({ href, label, active }: { href: string; label: string; active: boolean }) {
  return (
    <Link
      href={href}
      aria-current={active ? "page" : undefined}
      className={cn(
        "relative px-3 py-2 text-[0.8125rem] font-medium transition-colors",
        active ? "text-ink" : "text-ink-soft hover:text-ink"
      )}
    >
      <span className="sr-only">{label}</span>
      <span aria-hidden="true">
        <TextRoll lineHeight={1.25}>{label}</TextRoll>
      </span>
      <span
        aria-hidden="true"
        className={cn(
          "absolute inset-x-3 bottom-[5px] -z-10 h-[7px] origin-left bg-marker transition-transform duration-300 ease-out",
          active ? "scale-x-100" : "scale-x-0"
        )}
      />
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
          "relative flex items-center gap-1 px-3 py-2 text-[0.8125rem] font-medium transition-colors",
          active || open ? "text-ink" : "text-ink-soft hover:text-ink"
        )}
      >
        More
        <ChevronDown className={cn("h-3.5 w-3.5 transition-transform duration-200", open && "rotate-180")} />
        {active && (
          <span aria-hidden="true" className="absolute inset-x-3 bottom-[5px] -z-10 h-[7px] bg-marker" />
        )}
      </button>
      {open && (
        <div
          role="menu"
          className="panel absolute right-0 top-full z-50 mt-2 w-64 overflow-hidden p-1 shadow-[0_18px_40px_-18px_hsl(var(--ink)/0.35)] animate-rise"
        >
          <p className="label px-3 pb-1.5 pt-2.5">Also in HairGPT</p>
          {MORE_NAV.map(({ href, label, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              role="menuitem"
              onClick={() => setOpen(false)}
              className={cn(
                "flex items-center gap-2.5 rounded px-3 py-2.5 text-sm transition-colors",
                pathname.startsWith(href)
                  ? "bg-surface-sunken font-medium text-ink"
                  : "text-ink-soft hover:bg-surface-sunken hover:text-ink"
              )}
            >
              <Icon className="h-4 w-4 text-ink-faint" strokeWidth={1.75} />
              {label}
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

function Colophon() {
  return (
    <footer className="border-t border-rule print:hidden">
      <div className="container grid gap-8 py-10 text-sm md:grid-cols-[1.4fr_1fr_1fr]">
        <div>
          <p className="font-display text-xl italic leading-snug text-ink">Observations, not diagnoses.</p>
          <p className="mt-3 max-w-[58ch] text-[0.8125rem] leading-relaxed text-ink-soft">
            HairGPT measures what a photograph can show and says how sure it is. It never diagnoses and never
            prescribes; for anything that worries you, see a GP or a dermatologist.
          </p>
        </div>
        <div>
          <p className="label mb-3">Evidence</p>
          <ul className="space-y-1.5 text-[0.8125rem] text-ink-soft">
            <li>NHS, under the Open Government Licence v3</li>
            <li>MedlinePlus, NIAMS and DailyMed (US public domain)</li>
            <li>Europe PMC open-access reviews (CC BY / CC0)</li>
          </ul>
        </div>
        <div>
          <p className="label mb-3">Colophon</p>
          <ul className="space-y-1.5 text-[0.8125rem] text-ink-soft">
            <li>Set in Newsreader, Public Sans and IBM Plex Mono</li>
            <li className="flex flex-wrap items-center gap-1">
              Components by
              <Link001 href="https://skiper-ui.com" className="inline-flex text-ink">
                Skiper UI
              </Link001>
            </li>
          </ul>
        </div>
      </div>
    </footer>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-40 border-b border-rule bg-ground/85 backdrop-blur-md print:hidden">
        <div className="container flex h-16 items-center justify-between gap-4">
          <Wordmark />

          <nav className="isolate hidden items-center md:flex" aria-label="Primary">
            {NAV.map(({ href, label }) => (
              <NavLink key={href} href={href} label={label} active={isActive(pathname, href)} />
            ))}
            <MoreMenu pathname={pathname} />
          </nav>

          <div className="flex items-center gap-1.5">
            <ThemeToggle />
            <Link href="/assessment" className={cn(buttonVariants({ size: "sm" }), "hidden h-9 px-3.5 sm:inline-flex")}>
              <Plus className="h-3.5 w-3.5" strokeWidth={2.25} />
              New check
            </Link>
          </div>
        </div>
        {/* Content softens as it slides under the header (Skiper UI progressive blur). */}
        <div className="pointer-events-none absolute inset-x-0 top-full h-5">
          <ProgressiveBlur position="top" height="100%" blurAmount="2px" backgroundColor="hsl(var(--ground) / 0.7)" />
        </div>
      </header>

      <main className="container flex-1 pb-28 pt-8 md:pb-16 md:pt-12 print:p-0">{children}</main>

      <nav
        className="fixed inset-x-0 bottom-0 z-40 border-t border-rule bg-ground/95 backdrop-blur-lg md:hidden print:hidden"
        aria-label="Primary mobile"
      >
        <div className="grid grid-cols-5 px-2 pb-[max(env(safe-area-inset-bottom),0.35rem)] pt-1.5">
          {NAV.map(({ href, label, icon: Icon }) => {
            const active = isActive(pathname, href);
            return (
              <Link
                key={href}
                href={href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "relative flex flex-col items-center justify-center gap-1 py-1.5 transition-colors",
                  active ? "text-ink" : "text-ink-faint hover:text-ink"
                )}
              >
                <span
                  aria-hidden="true"
                  className={cn(
                    "absolute top-0 h-[3px] w-8 bg-marker transition-transform duration-300",
                    active ? "scale-x-100" : "scale-x-0"
                  )}
                />
                <Icon className="h-5 w-5" strokeWidth={active ? 2 : 1.6} />
                <span className="font-mono text-[9.5px] uppercase tracking-[0.08em]">{label}</span>
              </Link>
            );
          })}
        </div>
      </nav>

      <Colophon />
    </div>
  );
}
