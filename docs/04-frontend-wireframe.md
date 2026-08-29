# HairGPT — Frontend Wireframe & UX

**Feel:** Apple Health + Google Lens + a modern dermatologist dashboard + a calm AI assistant. Premium, clean, minimal, medical — **not** a chatbot, **not** a hospital admin system. Generous whitespace, one accent color, rounded cards, subtle depth, confidence shown as rings/meters, evidence always one tap away.

## Design tokens
- Type: Inter / system UI; large friendly numerals for metrics.
- Color: neutral slate canvas, single teal/emerald accent, semantic states (amber = caution, red = refer). Full dark mode.
- Components: shadcn/ui (Card, Button, Badge, Progress, Tabs, Dialog, Sheet, Tooltip).
- Every AI card has two affordances: **Why?** and **Evidence**.

## Screen map
```
/                     Home dashboard (Hair Health hero)
/scan/new             Domain picker (Hair / Skin)
/scan/hair            Guided capture — 7 views with live quality coaching
/scan/skin            Guided capture — 3 views
/scan/[id]/review     Per-view quality results + retake
/scan/[id]/result     Analysis: observations, safety, recommendations, Why/Evidence
/timeline             Longitudinal charts + treatment events + scan history
/compare              Before / After / Overlay / Diff
/treatments           Treatment tracker + adherence
/products             Product scanner + intelligence + recommendations
/skin                 SkinGPT dashboard (Skin Appearance Index)
/report/[id]          Doctor report preview & export
/settings             Consent, export, delete, privacy
```

## Home dashboard (the required first view)
A hero **Hair Health** card, then a metric grid — each is a tappable card with a confidence ring and a `Why?`:

```
┌───────────────────────────────────────────────┐
│  Hair Health                       ◐ 61% conf   │
│  "Stable — apparent"                            │
│  ▁▂▂▃▃▃  (sparkline of recent scans)            │
└───────────────────────────────────────────────┘
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ Hairline     │ │ Crown        │ │ Scalp vis.   │
│ apparent     │ │ apparent     │ │ 22%          │
│ stable ◐55%  │ │ stable ◐58%  │ │ ◐70%         │
└──────────────┘ └──────────────┘ └──────────────┘
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ Treatment    │ │ Last scan    │ │ Next scan    │
│ adherence 86%│ │ 12 days ago  │ │ in 18 days   │
└──────────────┘ └──────────────┘ └──────────────┘
[ New scan ]   [ Compare ]   [ Doctor report ]
```

Persistent footer disclaimer: *"HairGPT provides image-based observations, not a medical diagnosis."*

## Guided capture (Google-Lens feel)
- Full-bleed camera, an on-screen **silhouette guide** per view, and a live coaching chip: *"Hold steady"*, *"Too dark"*, *"Move closer"*, *"Part hair to show scalp"*.
- A capture is accepted only after a client-side pre-check; the server quality gate is authoritative and can still request a retake.
- Progress rail shows the 7 (or 3) views; completed views get a green check.

## Result screen
- Top: overall confidence ring + safety banner (green ok / amber caution / **red refer** takes over the screen and hides cosmetic advice).
- Observation cards grouped by region; each shows value, a `visual observation` vs `AI inference` badge, a `mock` badge when applicable, and Why?/Evidence.
- Recommendations grouped: *Care guidance*, *Discuss with a clinician*, *Referral* (if any). Prescription meds never appear as an app recommendation.

## Compare screen
Four synced panes: **Before | After | Aligned Overlay | Difference**, a metrics table (apparent delta + confidence per metric), and a limitations panel ("captured under different lighting", "alignment quality 0.74"). Fixed caption: *"Apparent changes only — images cannot prove treatment efficacy."*

## Timeline
Stacked small-multiples: hairline, crown, scalp visibility, apparent density; a treatment lane (start/stop bars); an adherence lane; scan markers. Tap any point → that scan. Confidence bands shaded; mock-derived points visually differentiated.

## Accessibility & trust
WCAG AA contrast, keyboard nav, screen-reader labels on every metric, motion-reduced mode, and confidence/limitations never hidden behind hover-only affordances.
