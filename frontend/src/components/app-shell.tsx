"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  ChevronDown,
  Sparkles,
  LayoutDashboard,
  ClipboardCheck,
  Activity,
  Calendar,
  Layers,
  Plus,
  Settings,
  Pill,
  ShoppingBag,
  History,
  ShieldCheck,
} from "lucide-react";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/assessment", label: "Assessment", icon: ClipboardCheck },
  { href: "/shedding", label: "Shedding", icon: Activity },
  { href: "/timeline", label: "Timeline", icon: Calendar },
  { href: "/compare", label: "Compare", icon: Layers },
];

const MORE_NAV = [
  { href: "/history", label: "Your History", icon: History },
  { href: "/treatments", label: "Treatments & Regimen", icon: Pill },
  { href: "/products", label: "Products & Ingredients", icon: ShoppingBag },
  { href: "/settings", label: "Settings & Privacy", icon: Settings },
];

function isActive(pathname: string, href: string) {
  return href === "/" ? pathname === "/" : pathname.startsWith(href);
}

function Wordmark() {
  return (
    <Link href="/" className="group flex items-center gap-2.5" aria-label="HairGPT home">
      <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-tr from-accent to-blue-400 text-white shadow-sm shadow-accent/25 transition-transform group-hover:scale-105">
        <Sparkles className="h-5 w-5" />
      </div>
      <div>
        <span className="text-lg font-bold tracking-tight text-ink">HairGPT</span>
        <span className="hidden select-none text-[10px] font-semibold tracking-wider text-ink-faint sm:block uppercase">
          Clinical Tracking & AI Insights
        </span>
      </div>
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
          "flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium transition-all",
          active
            ? "bg-accent-wash text-accent font-semibold"
            : "text-ink-soft hover:bg-surface-sunken hover:text-ink"
        )}
      >
        More
        <ChevronDown className={cn("h-4 w-4 transition-transform duration-200", open && "rotate-180")} />
      </button>
      {open && (
        <div
          role="menu"
          className="panel absolute right-0 top-full z-50 mt-2 w-64 overflow-hidden rounded-xl p-1.5 shadow-xl backdrop-blur-md animate-rise"
        >
          {MORE_NAV.map(({ href, label, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              role="menuitem"
              onClick={() => setOpen(false)}
              className={cn(
                "flex items-center gap-2.5 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                pathname.startsWith(href)
                  ? "bg-accent-wash text-accent"
                  : "text-ink-soft hover:bg-surface-sunken hover:text-ink"
              )}
            >
              <Icon className="h-4 w-4 text-ink-faint" />
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
    <div className="flex min-h-screen flex-col bg-ground">
      {/* Top Navbar */}
      <header className="sticky top-0 z-40 border-b bg-surface/90 backdrop-blur-md">
        <div className="container flex h-16 items-center justify-between gap-4">
          <Wordmark />

          {/* Desktop Navigation */}
          <nav className="hidden items-center gap-1 md:flex" aria-label="Primary">
            {NAV.map(({ href, label }) => {
              const active = isActive(pathname, href);
              return (
                <Link
                  key={href}
                  href={href}
                  aria-current={active ? "page" : undefined}
                  className={cn(
                    "relative rounded-lg px-3.5 py-2 text-sm font-medium transition-all",
                    active
                      ? "bg-accent-wash text-accent font-semibold shadow-xs"
                      : "text-ink-soft hover:bg-surface-sunken hover:text-ink"
                  )}
                >
                  {label}
                </Link>
              );
            })}
            <MoreMenu pathname={pathname} />
          </nav>

          {/* Header Action */}
          <div className="hidden items-center gap-3 sm:flex">
            <Link
              href="/assessment"
              className="inline-flex items-center gap-1.5 rounded-xl bg-accent px-4 py-2 text-sm font-medium text-white shadow-sm shadow-accent/30 hover:bg-accent/90 transition-all active:scale-95"
            >
              <Plus className="h-4 w-4" />
              <span>New Check</span>
            </Link>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="container flex-1 py-8 md:py-10 pb-24 md:pb-12">{children}</main>

      {/* Mobile Bottom Navigation Bar */}
      <nav
        className="fixed bottom-0 left-0 right-0 z-40 border-t bg-surface/95 backdrop-blur-lg md:hidden"
        aria-label="Primary mobile"
      >
        <div className="grid grid-cols-5 py-1.5 px-2">
          {NAV.map(({ href, label, icon: Icon }) => {
            const active = isActive(pathname, href);
            return (
              <Link
                key={href}
                href={href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "flex flex-col items-center justify-center gap-1 rounded-lg py-1.5 transition-colors",
                  active ? "text-accent font-semibold" : "text-ink-faint hover:text-ink"
                )}
              >
                <Icon className={cn("h-5 w-5", active && "text-accent stroke-[2.2]")} />
                <span className="text-[11px]">{label}</span>
              </Link>
            );
          })}
        </div>
      </nav>

      {/* Footer */}
      <footer className="border-t bg-surface-sunken">
        <div className="container flex flex-col gap-3 py-6 text-xs text-ink-faint">
          <div className="flex items-center gap-2 text-ink-soft font-medium">
            <ShieldCheck className="h-4 w-4 text-accent" />
            <span>Clinical Transparency & Privacy Safeguards</span>
          </div>
          <p className="max-w-[72ch] leading-relaxed">
            HairGPT produces image-based observations and AI inferences —{" "}
            <strong className="font-semibold text-ink-soft">not a medical diagnosis</strong>. It never prescribes
            medication. All computer-vision outputs are informational heuristics. Always consult a board-certified dermatologist for clinical diagnoses and treatment prescriptions.
          </p>
        </div>
      </footer>
    </div>
  );
}
