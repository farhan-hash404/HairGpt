import type { Metadata } from "next";
import { IBM_Plex_Mono, Newsreader, Public_Sans } from "next/font/google";
import "./globals.css";
import { AppShell } from "@/components/app-shell";

/* Three roles, deliberately paired:
   - Newsreader carries headings. This product cites AAD, NICE and NHS, so it
     should read like a journal rather than a consumer app.
   - Public Sans runs the interface. Institutional and plain-spoken.
   - IBM Plex Mono sets every measurement. The numbers are the product. */
const display = Newsreader({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  style: ["normal", "italic"],
  variable: "--font-display",
  display: "swap",
});

const sans = Public_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-sans",
  display: "swap",
});

const mono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "HairGPT",
  description:
    "Image-based hair and scalp observations with stated confidence, cited evidence, and clinician escalation. Not a medical diagnosis.",
};

/* Applies a saved light/dark choice before first paint, so the page never
   flashes the wrong theme. Without a saved choice the system setting rules. */
const THEME_BOOT = `try{var t=localStorage.getItem("hairgpt-theme");if(t==="light"||t==="dark")document.documentElement.dataset.theme=t}catch(e){}`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    // data-scroll-behavior: keep smooth in-page scrolling without Next 16
    // smooth-scrolling every route change.
    <html lang="en" suppressHydrationWarning data-scroll-behavior="smooth">
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_BOOT }} />
      </head>
      <body className={`${display.variable} ${sans.variable} ${mono.variable}`}>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
