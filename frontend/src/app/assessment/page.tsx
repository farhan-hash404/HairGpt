"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowLeft, ArrowRight, CheckCircle2, ShieldAlert } from "lucide-react";
import { api, EMPTY_HISTORY, type ClinicalHistory } from "@/lib/api";
import { AuthGate } from "@/components/auth-gate";
import { GuidedCapture } from "@/components/guided-capture";
import { Button } from "@/components/ui/button";
import {
  STEPS,
  StepPanel,
  StepRail,
  Fieldset,
  SkinTonePicker,
  PatternPicker,
  ChoiceCardGroup,
  TagChip,
  MedicationInput,
  type StepId,
} from "@/components/assessment/steps";
import {
  EMPTY_HAIR,
  EMPTY_SKIN,
  SymptomCheck,
  type HairSymptoms,
  type SkinSymptoms,
} from "@/components/symptom-check";

export default function AssessmentPage() {
  return (
    <AuthGate>
      <Assessment />
    </AuthGate>
  );
}

function Assessment() {
  const router = useRouter();
  const [step, setStep] = React.useState<StepId>("profile");
  const [furthest, setFurthest] = React.useState(0);
  const [saving, setSaving] = React.useState(false);

  const [profile, setProfile] = React.useState({
    year_of_birth: null as number | null,
    sex: null as string | null,
    fitzpatrick_self: null as number | null,
  });
  const [history, setHistory] = React.useState<ClinicalHistory>(EMPTY_HISTORY);
  const [hairSymptoms, setHairSymptoms] = React.useState<HairSymptoms>(EMPTY_HAIR);
  const [skinSymptoms] = React.useState<SkinSymptoms>(EMPTY_SKIN);

  const index = STEPS.findIndex((s) => s.id === step);

  React.useEffect(() => {
    (async () => {
      const [me, existing] = await Promise.all([
        api.me().catch(() => null),
        api.getHistory().catch(() => null),
      ]);
      if (me?.user) {
        setProfile({
          year_of_birth: me.user.year_of_birth ?? null,
          sex: me.user.sex ?? null,
          fitzpatrick_self: me.user.fitzpatrick_self ?? null,
        });
      }
      if (existing) setHistory({ ...EMPTY_HISTORY, ...existing });
    })();
  }, []);

  function goto(id: StepId, i: number) {
    setStep(id);
    setFurthest((f) => Math.max(f, i));
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function next() {
    setSaving(true);
    try {
      if (step === "profile") await api.updateProfile(profile);
      if (step === "story" || step === "health") await api.saveHistory(history);
      const target = STEPS[index + 1];
      if (target) goto(target.id, index + 1);
    } finally {
      setSaving(false);
    }
  }

  function back() {
    const target = STEPS[index - 1];
    if (target) goto(target.id, index - 1);
  }

  function setH<K extends keyof ClinicalHistory>(key: K, value: ClinicalHistory[K]) {
    setHistory((h) => ({ ...h, [key]: value }));
  }

  return (
    <div className="mx-auto max-w-5xl">
      <div className="grid gap-8 lg:grid-cols-[260px_minmax(0,1fr)]">
        {/* Progress Stepper Sidebar */}
        <aside className="lg:sticky lg:top-24 lg:self-start">
          <StepRail current={step} furthest={furthest} onJump={goto} />
        </aside>

        {/* Active Step Panel */}
        <div className="min-w-0 pb-16">
          {step === "profile" && (
            <StepPanel
              badge="Step 1 of 5"
              title="About You"
              intro="These optional questions help calibrate the computer vision models across diverse demographics to ensure unbiased, accurate readings for your specific hair and scalp type."
            >
              <Fieldset
                legend="Skin & Scalp Tone"
                hint="Selecting your skin tone allows the computer vision algorithm to tune its hair-to-scalp contrast detection properly."
              >
                <SkinTonePicker
                  value={profile.fitzpatrick_self}
                  onChange={(tone) => setProfile((p) => ({ ...p, fitzpatrick_self: tone }))}
                />
              </Fieldset>

              <Fieldset legend="Age Bracket">
                <ChoiceCardGroup
                  value={profile.year_of_birth ? bandOf(profile.year_of_birth) : null}
                  onChange={(v) => setProfile((p) => ({ ...p, year_of_birth: yearFromBand(v) }))}
                  options={AGE_BANDS.map((b) => ({ value: b, label: b }))}
                />
              </Fieldset>

              <Fieldset legend="Biological Sex">
                <ChoiceCardGroup
                  value={profile.sex}
                  onChange={(v) => setProfile((p) => ({ ...p, sex: v }))}
                  options={[
                    { value: "female", label: "Female" },
                    { value: "male", label: "Male" },
                    { value: "intersex", label: "Intersex" },
                    { value: "prefer_not_to_say", label: "Prefer not to say" },
                  ]}
                />
              </Fieldset>
            </StepPanel>
          )}

          {step === "story" && (
            <StepPanel
              badge="Step 2 of 5"
              title="Your Hair Story"
              intro="Understanding when and where thinning began is the strongest clinical indicator for determining the underlying cause."
            >
              <Fieldset legend="Where are you noticing thinning or shedding?">
                <PatternPicker
                  value={history.pattern}
                  onChange={(p) => setH("pattern", p)}
                />
              </Fieldset>

              <Fieldset legend="How did the hair changes begin?">
                <ChoiceCardGroup
                  value={history.onset}
                  onChange={(v) => setH("onset", v)}
                  options={[
                    { value: "gradual", label: "Gradual", description: "Slow change over months/years" },
                    { value: "sudden", label: "Sudden", description: "Noticeable rapid change over weeks" },
                    { value: "unsure", label: "Not sure", description: "Hard to specify" },
                  ]}
                />
              </Fieldset>

              <Fieldset legend="How many months has this been noticeable?">
                <div className="flex items-center gap-3">
                  <input
                    type="number"
                    min={0}
                    value={history.duration_months ?? ""}
                    onChange={(e) =>
                      setH("duration_months", e.target.value === "" ? null : Number(e.target.value))
                    }
                    placeholder="e.g. 6"
                    className="readout w-32 rounded border border-rule-strong bg-surface px-3.5 py-2.5 text-base focus:border-ink focus:outline-none focus:ring-2 focus:ring-marker/70"
                  />
                  <span className="label">months</span>
                </div>
              </Fieldset>

              <Fieldset legend="Family History">
                <div className="space-y-3">
                  <TagChip
                    label="Hair thinning or pattern loss runs in my family"
                    checked={Boolean(history.family_history_hair_loss)}
                    onChange={(v) => setH("family_history_hair_loss", v)}
                  />

                  {history.family_history_hair_loss && (
                    <div className="pt-2">
                      <p className="text-xs text-ink-faint mb-2">Which side of your family?</p>
                      <ChoiceCardGroup
                        value={history.family_history_side}
                        onChange={(v) => setH("family_history_side", v)}
                        options={[
                          { value: "maternal", label: "Mother's side" },
                          { value: "paternal", label: "Father's side" },
                          { value: "both", label: "Both sides" },
                          { value: "unsure", label: "Not sure" },
                        ]}
                      />
                    </div>
                  )}
                </div>
              </Fieldset>
            </StepPanel>
          )}

          {step === "health" && (
            <StepPanel
              badge="Step 3 of 5"
              title="Health & Daily Habits"
              intro="Non-genetic factors like nutrient deficiencies, stress, thyroid changes, and styling practices frequently trigger temporary shedding (telogen effluvium). Select any that apply."
            >
              <Fieldset legend="Diagnosed Medical Conditions">
                <div className="flex flex-wrap gap-2.5">
                  {(
                    [
                      ["iron_deficiency", "Iron Deficiency or Anaemia"],
                      ["thyroid_condition", "Thyroid Condition (Hypo/Hyper)"],
                      ["pcos", "PCOS"],
                      ["autoimmune_condition", "Autoimmune Condition"],
                      ["scalp_condition", "Diagnosed Scalp Condition (Psoriasis, Dermatitis)"],
                    ] as const
                  ).map(([key, label]) => (
                    <TagChip
                      key={key}
                      label={label}
                      checked={Boolean(history[key])}
                      onChange={(v) => setH(key, v as never)}
                    />
                  ))}
                </div>
              </Fieldset>

              <Fieldset
                legend="Events in the Past 12 Months"
                hint="Physical stressors often trigger shedding 2 to 4 months after the event occurs."
              >
                <div className="flex flex-wrap gap-2.5">
                  {(
                    [
                      ["major_stress", "Period of Major Stress"],
                      ["recent_illness", "Significant Illness / High Fever"],
                      ["recent_surgery", "Surgery under Anaesthesia"],
                      ["rapid_weight_loss", "Rapid Weight Loss or Strict Diet"],
                      ["postpartum", "Childbirth (Postpartum)"],
                    ] as const
                  ).map(([key, label]) => (
                    <TagChip
                      key={key}
                      label={label}
                      checked={Boolean(history[key])}
                      onChange={(v) => setH(key, v as never)}
                    />
                  ))}
                </div>
              </Fieldset>

              <Fieldset
                legend="Hair Styling Practices"
                hint="Tension and harsh chemicals can cause traction alopecia or strand breakage."
              >
                <div className="flex flex-wrap gap-2.5">
                  {(
                    [
                      ["tight_hairstyles", "Tight braids, weaves, or tight ponytails"],
                      ["chemical_treatments", "Frequent relaxers, bleach, or perms"],
                      ["heat_styling", "Frequent high-heat blow drying or flat irons"],
                    ] as const
                  ).map(([key, label]) => (
                    <TagChip
                      key={key}
                      label={label}
                      checked={Boolean(history[key])}
                      onChange={(v) => setH(key, v as never)}
                    />
                  ))}
                </div>
              </Fieldset>

              <Fieldset legend="Regular Medications & Supplements">
                <MedicationInput
                  medications={history.medications}
                  onChange={(meds) => setH("medications", meds)}
                />
              </Fieldset>
            </StepPanel>
          )}

          {step === "safety" && (
            <StepPanel
              badge="Step 4 of 5"
              title="Clinical Safety Check"
              intro="HairGPT employs safety heuristics to detect red-flag symptoms. If any critical signs are present, the system prioritizes doctor escalation over routine tracking."
            >
              <SymptomCheck
                domain="hair"
                hair={hairSymptoms}
                skin={skinSymptoms}
                onHairChange={setHairSymptoms}
                onSkinChange={() => {}}
              />

              <div className="mt-6 border-t border-rule pt-6 space-y-3">
                <p className="label">Additional scalp sensations</p>
                <div className="flex flex-wrap gap-2.5">
                  <TagChip
                    label="Painful, burning, or tender scalp"
                    checked={Boolean(history.scalp_pain)}
                    onChange={(v) => setH("scalp_pain", v)}
                  />
                  <TagChip
                    label="Persistent itching or flaking"
                    checked={Boolean(history.scalp_itch)}
                    onChange={(v) => setH("scalp_itch", v)}
                  />
                </div>
              </div>
            </StepPanel>
          )}

          {step === "capture" && (
            <StepPanel
              badge="Step 5 of 5"
              title="Guided Photo Scan"
              intro="Follow the live on-screen guides to capture each angle. You can use your phone's camera directly or upload high-resolution photos."
            >
              <GuidedCapture
                domain="hair"
                presetSymptoms={hairSymptoms}
                onComplete={(sessionId) => router.push(`/scan/${sessionId}/result`)}
              />
            </StepPanel>
          )}

          {/* Navigation Controls (Desktop and Mobile sticky bar) */}
          {step !== "capture" && step !== "reading" && (
            <div className="mt-8 flex items-center justify-between border-t border-rule pt-6">
              <Button
                variant="outline"
                size="lg"
                onClick={back}
                disabled={index === 0}
                className="gap-2"
              >
                <ArrowLeft className="h-4 w-4" />
                <span>Back</span>
              </Button>

              <div className="flex items-center gap-4">
                <Link
                  href="/"
                  className="text-xs font-medium text-ink-faint hover:text-ink transition-colors"
                >
                  Save & Exit
                </Link>
                <Button size="lg" onClick={next} disabled={saving} className="gap-2 px-6">
                  <span>{saving ? "Saving…" : index === STEPS.length - 2 ? "Start Camera Scan" : "Continue"}</span>
                  <ArrowRight className="h-4 w-4" />
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

const AGE_BANDS = ["Under 25", "25–34", "35–44", "45–54", "55–64", "65+"];

function yearFromBand(band: string): number {
  const now = new Date().getFullYear();
  const midpoint: Record<string, number> = {
    "Under 25": 20,
    "25–34": 30,
    "35–44": 40,
    "45–54": 50,
    "55–64": 60,
    "65+": 70,
  };
  return now - (midpoint[band] ?? 30);
}

function bandOf(year: number): string {
  const age = new Date().getFullYear() - year;
  if (age < 25) return "Under 25";
  if (age < 35) return "25–34";
  if (age < 45) return "35–44";
  if (age < 55) return "45–54";
  if (age < 65) return "55–64";
  return "65+";
}
