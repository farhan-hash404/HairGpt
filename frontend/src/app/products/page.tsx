"use client";

import * as React from "react";
import { AlertTriangle, Check, FlaskConical } from "lucide-react";
import { api } from "@/lib/api";
import { AuthGate } from "@/components/auth-gate";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/page-header";
import { Link001 } from "@/components/ui/skiper-ui/skiper40";
import { cn } from "@/lib/utils";

// Hair-only: the skin goals left with the skin domain.
const GOALS = ["reduce shedding", "scalp comfort", "hydration"];

export default function ProductsPage() {
  return (
    <AuthGate>
      <Products />
    </AuthGate>
  );
}

function Products() {
  const [goals, setGoals] = React.useState<string[]>([]);
  const [budget, setBudget] = React.useState("");
  // The product ships one domain; evidence retrieval is still domain-scoped.
  const domain = "hair";
  const [result, setResult] = React.useState<any>(null);
  const [busy, setBusy] = React.useState(false);

  async function run() {
    setBusy(true);
    try {
      setResult(await api.recommendProducts({ goals, budget: budget || null, regimen_product_ids: [], domain }));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-4xl animate-rise">
      <PageHeader
        index="Nº 08"
        eyebrow="Products & ingredients"
        title={
          <>
            Ingredients, <span className="italic text-ink-soft">not</span> <span className="marker">adverts</span>.
          </>
        }
        dek="Evidence-gated, ingredient-aware suggestions. Nothing is ranked by affiliate revenue; the system has no affiliate data at all."
      />

      <section className="crop-marks">
        <div className="space-y-6 border border-rule bg-surface p-5 sm:p-7">
          <div>
            <p className="mb-3 font-display text-xl">What are you trying to improve?</p>
            <div className="flex flex-wrap gap-2">
              {GOALS.map((g) => {
                const on = goals.includes(g);
                return (
                  <button
                    key={g}
                    type="button"
                    aria-pressed={on}
                    onClick={() => setGoals(on ? goals.filter((x) => x !== g) : [...goals, g])}
                    className={cn(
                      "inline-flex items-center gap-2 rounded border px-3 py-2 text-sm transition-colors",
                      on ? "border-ink bg-ink text-ground" : "border-rule-strong bg-surface text-ink hover:bg-surface-sunken"
                    )}
                  >
                    <span
                      className={cn(
                        "flex h-4 w-4 items-center justify-center rounded-sm border",
                        on ? "border-marker bg-marker text-[hsl(30_12%_10%)]" : "border-ink-faint"
                      )}
                    >
                      {on && <Check className="h-3 w-3" strokeWidth={3} />}
                    </span>
                    {g}
                  </button>
                );
              })}
            </div>
          </div>

          <div className="flex flex-wrap items-end gap-3 border-t border-rule pt-5">
            <label className="block">
              <span className="label mb-1.5 block">Budget (optional)</span>
              <input
                value={budget}
                onChange={(e) => setBudget(e.target.value)}
                placeholder="e.g. under $30"
                className="rounded border border-rule-strong bg-surface px-3.5 py-2.5 text-sm placeholder:text-ink-faint focus:border-ink focus:outline-none focus:ring-2 focus:ring-marker/70"
              />
            </label>
            <Button onClick={run} disabled={busy}>
              <FlaskConical className="h-4 w-4" strokeWidth={1.75} /> {busy ? "Checking evidence…" : "Get suggestions"}
            </Button>
          </div>
        </div>
      </section>

      {result && (
        <div className="mt-12 space-y-10">
          {!!result.ingredient_conflicts?.length && (
            <section className="border-l-2 border-caution bg-caution-wash px-5 py-4">
              <p className="flex items-center gap-2 font-medium text-caution">
                <AlertTriangle className="h-4 w-4" /> Ingredient conflicts in your regimen
              </p>
              <ul className="mt-3 space-y-2 text-sm">
                {result.ingredient_conflicts.map((c: any, i: number) => (
                  <li key={i}>
                    <p className="readout font-medium">{c.between.join(" + ")}</p>
                    <p className="text-ink-soft">{c.note}</p>
                  </li>
                ))}
              </ul>
            </section>
          )}

          <section>
            <h2 className="mb-4 flex items-baseline gap-3 text-2xl">
              <span className="readout text-sm text-ink-faint">A.</span>
              Evidence-backed suggestions
            </h2>
            <ol className="border-t border-ink">
              {result.evidence_backed_suggestions.map((s: any, i: number) => (
                <li key={i} className="grid gap-x-5 border-b border-rule py-5 md:grid-cols-[2.5rem_1fr]">
                  <span className="readout pt-1 text-xs text-ink-faint">{String(i + 1).padStart(2, "0")}</span>
                  <div>
                    <div className="mb-2 flex flex-wrap items-center gap-1.5">
                      <Badge variant="neutral">{s.source}</Badge>
                      {s.evidence_grade && <Badge variant="flag">{s.evidence_grade.replace(/_/g, " ")}</Badge>}
                    </div>
                    <p className="font-display text-lg leading-snug">{s.suggestion}</p>
                    <Link001 href={s.url} className="mt-2 inline-flex text-xs text-ink-soft">
                      Based on: {s.based_on}
                    </Link001>
                  </div>
                </li>
              ))}
            </ol>
            <p className="caption mt-4 max-w-[80ch]">
              Ranking basis: {result.ranking_basis}. {result.disclaimer}
            </p>
          </section>
        </div>
      )}
    </div>
  );
}
