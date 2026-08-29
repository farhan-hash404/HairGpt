"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  Camera,
  FlaskConical,
  LineChart,
  Pill,
  ScanFace,
  Settings,
  Sparkles,
} from "lucide-react";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/", label: "Home", icon: Activity },
  { href: "/scan/hair", label: "Hair scan", icon: Camera },
  { href: "/skin", label: "SkinGPT", icon: ScanFace },
  { href: "/timeline", label: "Timeline", icon: LineChart },
  { href: "/compare", label: "Compare", icon: Sparkles },
  { href: "/treatments", label: "Treatments", icon: Pill },
  { href: "/products", label: "Products", icon: FlaskConical },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-40 border-b bg-background/80 backdrop-blur">
        <div className="container flex h-16 items-center justify-between gap-4">
          <Link href="/" className="flex items-center gap-2">
            <span className="grid h-8 w-8 place-items-center rounded-xl bg-primary text-primary-foreground">
              <Activity className="h-4 w-4" />
            </span>
            <span className="text-lg font-semibold tracking-tight">HairGPT</span>
          </Link>
          <nav className="hidden items-center gap-1 md:flex" aria-label="Primary">
            {NAV.map(({ href, label, icon: Icon }) => {
              const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
              return (
                <Link
                  key={href}
                  href={href}
                  aria-current={active ? "page" : undefined}
                  className={cn(
                    "flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm transition-colors",
                    active ? "bg-accent text-accent-foreground" : "text-muted-foreground hover:bg-muted"
                  )}
                >
                  <Icon className="h-3.5 w-3.5" />
                  {label}
                </Link>
              );
            })}
          </nav>
        </div>
      </header>

      <main className="container flex-1 py-8">{children}</main>

      {/* Mobile nav */}
      <nav
        className="sticky bottom-0 z-40 grid grid-cols-5 border-t bg-background/95 backdrop-blur md:hidden"
        aria-label="Primary mobile"
      >
        {NAV.slice(0, 5).map(({ href, label, icon: Icon }) => {
          const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex flex-col items-center gap-0.5 py-2 text-[10px]",
                active ? "text-primary" : "text-muted-foreground"
              )}
            >
              <Icon className="h-4 w-4" />
              {label}
            </Link>
          );
        })}
      </nav>

      <footer className="border-t py-5">
        <div className="container text-xs text-muted-foreground">
          HairGPT provides image-based observations and AI inferences — <strong>not a medical diagnosis</strong>. It
          never prescribes medication. Always consult a qualified clinician for diagnosis and treatment.
        </div>
      </footer>
    </div>
  );
}
