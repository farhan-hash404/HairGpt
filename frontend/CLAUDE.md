@AGENTS.md

## Design: the annotated clinical atlas

HairGPT measures, then cites, so the UI borrows from a dermatology atlas (serif
plates, figure captions, numbered references) and a lab instrument (mono
readouts, ruler ticks, crop marks). Keep new screens in this language:

- Tokens only (`src/app/globals.css`): warm paper `ground`/`surface`, `ink`,
  `accent` (surgical green: links, focus), `marker` (highlighter: emphasis fills
  only, never text or state), and `ok`/`caution`/`alert` for safety states only.
  No raw Tailwind palette colours (`blue-500`, `slate-…`), no gradients, no glows.
- Primary buttons are ink (`buttonVariants()`); hover runs the highlighter.
  Put `buttonVariants` on a `<Link>` rather than nesting a `<Button>` in it.
- Pages open with `<PageHeader index="Nº 0x" …>`; sections are lettered
  (`A.`, `B.`) serif h2s; lists are ruled registers (`border-t border-ink`,
  `border-b border-rule`) rather than card grids.
- Numbers use `<Readout>`/`<PercentReadout>` (count up once in view) or
  `.readout`; small labels use `.label`; figure notes use `.caption`.
- Photos and charts sit in `.crop-marks`, charts on `.graph-paper`.
- Confidence is ink (never green: green would read as "good").
- No emoji and no celebratory copy: describe change in points against noise.

## UI components: Skiper UI

Animated and interactive pieces come from [Skiper UI](https://skiper-ui.com), installed
through the shadcn CLI. It is an effects library (37 components: carousels, scroll
effects, animated numbers, tooltips, theme toggles), not a UI kit. Buttons, cards, badges
and forms stay on this site's own components in `src/components/ui/` and its design tokens.

- Browse: `npx shadcn@latest search @skiper-ui --limit 40`
- Inspect before adding (files, npm dependencies, registryDependencies, cssVars):
  `npx shadcn@latest view @skiper-ui/skiperNN`
- Add: `npx shadcn@latest add @skiper-ui/skiperNN`, which writes
  `src/components/ui/skiper-ui/skiperNN.tsx`

In use: text roll nav (skiper58), animated source links (skiper40), progressive
blur under the header (skiper41), tooltip (skiper101, remapped to site tokens).
Adapted rather than vendored: the theme toggle (`components/theme-toggle.tsx`,
from skiper4, whose registry SVG data is corrupted), measurement readouts
(`components/readout.tsx`, the skiper37 NumberFlow pattern) and the compare
strip (`components/compare-panes.tsx`, skiper52's hover-expand for any content).

Rules:

- Never run `npx shadcn init`. It rewrites `src/app/globals.css` and `tailwind.config.ts`
  with shadcn's default theme; `components.json` is hand-written (`cssVariables: false`)
  so that `add` works without it.
- After every `add`, check `git diff` on `globals.css`, `tailwind.config.ts` and
  `package.json`. Reject anything that redefines this site's tokens (`--accent`, `--ring`,
  `--radius`, ...) or overwrites `src/components/ui/{button,card,badge}.tsx`: those are
  this site's own components, not shadcn's.
- Tailwind here is v3.4; Skiper is written for v4. Translate v4-only classes when adopting
  a component (`z-1` to `z-[1]`, `bg-linear-to-r` to `bg-gradient-to-r`, `shadow-xs` to
  `shadow-sm`, `rounded-xs` to `rounded-sm`, `outline-hidden` to `outline-none`) and check
  it in the browser, because unknown classes fail silently.
- Replace hard-coded colours (`bg-white`, `text-black`, `bg-neutral-900`) with the site
  tokens (`bg-surface`, `text-ink`, `bg-accent`, ...) so light and dark themes keep working.
- Honour `prefers-reduced-motion`, and keep clinical screens calm: effects belong on
  navigation, the landing page and data reveals, never on safety banners, referral
  messages or anything a worried user must read.
- Skiper's free licence requires attribution: keep a "Components by Skiper UI" credit
  link in the site footer whenever a Skiper component ships.
