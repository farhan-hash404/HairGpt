import type { Config } from "tailwindcss";
import animate from "tailwindcss-animate";

const config: Config = {
  // Theming is driven entirely by CSS variables (system + explicit override),
  // so the `dark:` variant keys off the same data-theme attribute rather than a
  // separate class that could drift out of sync with the tokens.
  darkMode: ["variant", ['&:where([data-theme="dark"] *)', "@media (prefers-color-scheme: dark)"]],
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    container: { center: true, padding: "1.5rem", screens: { "2xl": "1180px" } },
    extend: {
      colors: {
        ground: "hsl(var(--ground) / <alpha-value>)",
        surface: {
          DEFAULT: "hsl(var(--surface) / <alpha-value>)",
          sunken: "hsl(var(--surface-sunken) / <alpha-value>)",
        },
        ink: {
          DEFAULT: "hsl(var(--ink) / <alpha-value>)",
          soft: "hsl(var(--ink-soft) / <alpha-value>)",
          faint: "hsl(var(--ink-faint) / <alpha-value>)",
        },
        rule: {
          DEFAULT: "hsl(var(--rule) / <alpha-value>)",
          strong: "hsl(var(--rule-strong) / <alpha-value>)",
        },
        accent: {
          DEFAULT: "hsl(var(--accent) / <alpha-value>)",
          ink: "hsl(var(--accent-ink) / <alpha-value>)",
          wash: "hsl(var(--accent-wash) / <alpha-value>)",
          edge: "hsl(var(--accent-edge) / <alpha-value>)",
        },
        ok: { DEFAULT: "hsl(var(--ok) / <alpha-value>)", wash: "hsl(var(--ok-wash) / <alpha-value>)" },
        caution: { DEFAULT: "hsl(var(--caution) / <alpha-value>)", wash: "hsl(var(--caution-wash) / <alpha-value>)" },
        alert: { DEFAULT: "hsl(var(--alert) / <alpha-value>)", wash: "hsl(var(--alert-wash) / <alpha-value>)" },
        // A highlighter: emphasis fills only, never text and never a state.
        marker: "hsl(var(--marker) / <alpha-value>)",
      },
      borderColor: { DEFAULT: "hsl(var(--rule))" },
      borderRadius: {
        DEFAULT: "var(--radius)",
        md: "var(--radius)",
        lg: "var(--radius-lg)",
        // Pages ask for xl/2xl in places; paper does not do bubbles.
        xl: "var(--radius-xl)",
        "2xl": "var(--radius-xl)",
      },
      fontFamily: {
        display: ["var(--font-display)", "ui-serif", "Georgia", "serif"],
        sans: ["var(--font-sans)", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "SFMono-Regular", "monospace"],
      },
      fontSize: {
        // A deliberate scale; everything sits on it.
        "2xs": ["0.6875rem", { lineHeight: "1rem" }],
        xs: ["0.75rem", { lineHeight: "1.1rem" }],
        sm: ["0.8125rem", { lineHeight: "1.35rem" }],
        base: ["0.9375rem", { lineHeight: "1.6rem" }],
        lg: ["1.0625rem", { lineHeight: "1.65rem" }],
        xl: ["1.375rem", { lineHeight: "1.35" }],
        "2xl": ["1.75rem", { lineHeight: "1.2" }],
        "3xl": ["2.25rem", { lineHeight: "1.1" }],
        "4xl": ["3rem", { lineHeight: "1.03" }],
        "5xl": ["3.75rem", { lineHeight: "1" }],
        "6xl": ["4.75rem", { lineHeight: "0.95" }],
      },
      keyframes: {
        rise: {
          from: { opacity: "0", transform: "translateY(8px)" },
          to: { opacity: "1", transform: "none" },
        },
        sweep: {
          from: { transform: "scaleX(0)" },
          to: { transform: "scaleX(1)" },
        },
      },
      animation: {
        rise: "rise .4s cubic-bezier(.2,.6,.2,1) both",
        sweep: "sweep .7s cubic-bezier(.2,.7,.2,1) both",
      },
    },
  },
  plugins: [animate],
};

export default config;
