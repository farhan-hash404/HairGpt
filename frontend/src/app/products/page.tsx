"use client";

import * as React from "react";
import { AlertTriangle, FlaskConical } from "lucide-react";
import { api } from "@/lib/api";
import { AuthGate } from "@/components/auth-gate";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const GOALS = ["reduce shedding", "scalp comfort", "hydration", "acne", "pigmentation", "sun protection"];

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
  const [domain, setDomain] = React.useState<"hair" | "skin">("hair");
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
    <div className="mx-auto max-w-3xl space-y-6">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Product intelligence</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Ingredient-aware, evidence-gated suggestions. Ranking never uses affiliate revenue — the system has no
          affiliate data.
        </p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>What are you trying to improve?</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-2">
            {GOALS.map((g) => {
              const on = goals.includes(g);
              return (
                <button
                  key={g}
                  onClick={() => setGoals(on ? goals.filter((x) => x !== g) : [...goals, g])}
                  className={`rounded-full border px-3 py-1.5 text-sm transition-colors ${
                    on ? "border-primary bg-primary/10 text-primary" : "text-muted-foreground hover:bg-muted"
                  }`}
                >
                  {g}
                </button>
              );
            })}
          </div>

          <div className="flex flex-wrap items-end gap-3">
            <label className="text-sm">
              <span className="mb-1 block font-medium">Domain</span>
              <select
                value={domain}
                onChange={(e) => setDomain(e.target.value as "hair" | "skin")}
                className="rounded-xl border bg-background px-3 py-2"
              >
                <option value="hair">Hair &amp; scalp</option>
                <option value="skin">Skin</option>
              </select>
            </label>
            <label className="text-sm">
              <span className="mb-1 block font-medium">Budget (optional)</span>
              <input
                value={budget}
                onChange={(e) => setBudget(e.target.value)}
                placeholder="e.g. under $30"
                className="rounded-xl border bg-background px-3 py-2"
              />
            </label>
            <Button onClick={run} disabled={busy}>
              <FlaskConical className="h-4 w-4" /> {busy ? "Checking evidence…" : "Get suggestions"}
            </Button>
          </div>
        </CardContent>
      </Card>

      {result && (
        <>
          {!!result.ingredient_conflicts?.length && (
            <Card className="border-[hsl(var(--caution))]/40">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-[hsl(var(--caution))]">
                  <AlertTriangle className="h-4 w-4" /> Ingredient conflicts in your regimen
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2 text-sm">
                  {result.ingredient_conflicts.map((c: any, i: number) => (
                    <li key={i} className="rounded-xl border p-3">
                      <p className="font-medium">{c.between.join(" + ")}</p>
                      <p className="text-muted-foreground">{c.note}</p>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}

          <Card>
            <CardHeader>
              <CardTitle>Evidence-backed suggestions</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-3">
                {result.evidence_backed_suggestions.map((s: any, i: number) => (
                  <li key={i} className="rounded-xl border p-4">
                    <div className="mb-1.5 flex flex-wrap items-center gap-2">
                      <Badge variant="secondary">{s.source}</Badge>
                      {s.evidence_grade && <Badge variant="outline">{s.evidence_grade.replace(/_/g, " ")}</Badge>}
                    </div>
                    <p className="font-medium">{s.suggestion}</p>
                    <a
                      href={s.url}
                      target="_blank"
                      rel="noreferrer"
                      className="mt-1 inline-block text-xs text-muted-foreground underline-offset-2 hover:underline"
                    >
                      Based on: {s.based_on}
                    </a>
                  </li>
                ))}
              </ul>
              <p className="mt-4 text-xs text-muted-foreground">
                Ranking basis: {result.ranking_basis}. {result.disclaimer}
              </p>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
