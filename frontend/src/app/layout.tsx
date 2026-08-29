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
    "Image-based hair, scalp and skin observations with stated confidence, cited evidence, and clinician escalation. Not a medical diagnosis.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${display.variable} ${sans.variable} ${mono.variable}`}>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
