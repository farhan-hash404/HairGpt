"use client";

import * as React from "react";
import { ShieldAlert } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

/**
 * Self-reported safety questions.
 *
 * Several high-severity red flags (scarring, pustules, sudden patchy loss,
 * facial swelling) cannot be reliably detected from photos. Asking directly is
 * the honest way to keep the safety net real — a single "yes" forces a clinician
 * referral and suppresses all cosmetic guidance for that scan.
 */

export type HairSymptoms = {
  pustules: boolean;
  boggy_scalp: boolean;
  scarring_signal: boolean;
  sudden_patchy_loss: boolean;
  systemic_symptoms: boolean;
};

export type SkinSymptoms = {
  lesion_abcde_signal: number;
  lesion_change_delta: number;
  facial_swelling: boolean;
  allergic_reaction: boolean;
  infection_like: boolean;
  systemic_symptoms: boolean;
};

const HAIR_QUESTIONS: { key: keyof HairSymptoms; label: string }[] = [
  { key: "pustules", label: "Pus-filled spots, crusting, or oozing on your scalp" },
  { key: "boggy_scalp", label: "Scalp that feels boggy, swollen, or painful to touch" },
  { key: "scarring_signal", label: "Smooth, shiny patches where hair follicles look absent" },
  { key: "sudden_patchy_loss", label: "Hair lost suddenly in well-defined round patches" },
  { key: "systemic_symptoms", label: "Fever, unexplained weight loss, or feeling generally unwell" },
];

const SKIN_QUESTIONS: { key: keyof SkinSymptoms; label: string; numeric?: boolean }[] = [
  { key: "lesion_abcde_signal", label: "A mole or spot that is asymmetric, irregular, multi-colored, or large", numeric: true },
  { key: "lesion_change_delta", label: "A lesion that has changed noticeably in recent weeks", numeric: true },
  { key: "facial_swelling", label: "Swelling of your face, lips, eyes, or tongue" },
  { key: "allergic_reaction", label: "Signs of a severe allergic reaction" },
  { key: "infection_like", label: "Spreading redness, warmth, or pus" },
  { key: "systemic_symptoms", label: "Fever or feeling generally unwell" },
];

export const EMPTY_HAIR: HairSymptoms = {
  pustules: false,
  boggy_scalp: false,
  scarring_signal: false,
  sudden_patchy_loss: false,
  systemic_symptoms: false,
};

export const EMPTY_SKIN: SkinSymptoms = {
  lesion_abcde_signal: 0,
  lesion_change_delta: 0,
  facial_swelling: false,
  allergic_reaction: false,
  infection_like: false,
  systemic_symptoms: false,
};

export function SymptomCheck({
  domain,
  hair,
  skin,
  onHairChange,
  onSkinChange,
}: {
  domain: "hair" | "skin";
  hair: HairSymptoms;
  skin: SkinSymptoms;
  onHairChange: (v: HairSymptoms) => void;
  onSkinChange: (v: SkinSymptoms) => void;
}) {
  const questions = domain === "hair" ? HAIR_QUESTIONS : SKIN_QUESTIONS;

  const anyChecked =
    domain === "hair"
      ? Object.values(hair).some(Boolean)
      : Object.values(skin).some((v) => (typeof v === "number" ? v > 0 : v));

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <ShieldAlert className="h-4 w-4 text-[hsl(var(--caution))]" />
          Safety check
        </CardTitle>
        <p className="text-sm text-muted-foreground">
          Photos can&apos;t show everything. Tick anything you&apos;ve noticed — these are things a clinician should look
          at, and we&apos;d rather send you to one than miss them.
        </p>
      </CardHeader>
      <CardContent className="space-y-2">
        {questions.map((q) => {
          const checked =
            domain === "hair"
              ? (hair[q.key as keyof HairSymptoms] as boolean)
              : typeof skin[q.key as keyof SkinSymptoms] === "number"
                ? (skin[q.key as keyof SkinSymptoms] as number) > 0
                : (skin[q.key as keyof SkinSymptoms] as unknown as boolean);

          return (
            <label
              key={String(q.key)}
              className="flex cursor-pointer items-start gap-3 rounded-xl border p-3 text-sm hover:bg-muted/40"
            >
              <input
                type="checkbox"
                checked={!!checked}
                onChange={(e) => {
                  const on = e.target.checked;
                  if (domain === "hair") {
                    onHairChange({ ...hair, [q.key]: on });
                  } else if ("numeric" in q && q.numeric) {
                    // Numeric signals map to a value the safety rules threshold on.
                    onSkinChange({ ...skin, [q.key]: on ? 1 : 0 });
                  } else {
                    onSkinChange({ ...skin, [q.key]: on } as SkinSymptoms);
                  }
                }}
                className="mt-0.5 h-4 w-4 accent-[hsl(var(--primary))]"
              />
              <span>{q.label}</span>
            </label>
          );
        })}

        {anyChecked && (
          <div className="rounded-xl border border-destructive/40 bg-destructive/5 p-3 text-sm">
            <p className="font-medium">We&apos;ll recommend seeing a clinician.</p>
            <p className="mt-0.5 text-muted-foreground">
              Because you flagged something above, this scan will skip cosmetic and self-treatment suggestions and
              recommend professional evaluation instead.
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
