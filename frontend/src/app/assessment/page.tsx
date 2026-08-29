"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowLeft, ArrowRight } from "lucide-react";
import { api, EMPTY_HISTORY, type ClinicalHistory } from "@/lib/api";
import { AuthGate } from "@/components/auth-gate";
import { GuidedCapture } from "@/components/guided-capture";
import { Button } from "@/components/ui/button";
import {
  CheckRow,
  ChoiceGroup,
  Fieldset,
  STEPS,
  StepPanel,
  StepRail,
  type StepId,
} from "@/components/assessment/steps";
import {
  EMPTY_HAIR,
  SymptomCheck,
  type HairSymptoms,
  type SkinSymptoms,
} from "@/components/symptom-check";
import { EMPTY_SKIN } from "@/components/symptom-check";

/**
 * The full assessment: history first, then images, then a reading.
 *
 * The ordering is the point. A clinician takes a history before they look, and
 * several of the most common causes of hair loss — thyroid disease, iron
 * deficiency, a drug side effect, shedding after illness — are invisible to any
 * camera. Capturing photos first and asking questions later would produce a
 * confident-looking reading built on the least informative input.
 */
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
  const [medInput, setMedInput] = React.useState("");

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
      // Persist as we go, so a dropped connection never costs the user their answers.
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
    <div className="grid gap-10 lg:grid-cols-[220px_minmax(0,1fr)]">
      <aside className="lg:sticky lg:top-20 lg:self-start">
        <p className="label mb-3 hidden lg:block">Assessment</p>
        <StepRail current={step} furthest={furthest} onJump={goto} />
      </aside>

      <div className="min-w-0">
        {step === "profile" && (
          <StepPanel
            title="About you"
            intro="Three optional questions. They exist so this product can report how well it performs for people like you rather than hiding behind an average — and for nothing else."
          >
            <Fieldset
              legend="Skin tone"
              hint="Image models frequently perform worse on darker skin. Recording this is how that gets measured instead of overlooked. Skip it if you'd rather not say."
            >
              <ChoiceGroup
                value={profile.fitzpatrick_self ? String(profile.fitzpatrick_self) : null}
                onChange={(v) => setProfile((p) => ({ ...p, fitzpatrick_self: Number(v) }))}
                options={[
                  { value: "1", label: "I — always burns" },
                  { value: "2", label: "II — usually burns" },
                  { value: "3", label: "III — sometimes burns" },
                  { value: "4", label: "IV — rarely burns" },
                  { value: "5", label: "V — very rarely burns" },
                  { value: "6", label: "VI — never burns" },
                ]}
              />
            </Fieldset>

            <Fieldset legend="Age band">
              <ChoiceGroup
                value={profile.year_of_birth ? bandOf(profile.year_of_birth) : null}
                onChange={(v) => setProfile((p) => ({ ...p, year_of_birth: yearFromBand(v) }))}
                options={AGE_BANDS.map((b) => ({ value: b, label: b }))}
              />
            </Fieldset>

            <Fieldset legend="Sex">
              <ChoiceGroup
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
            title="Your hair story"
            intro="How something started often narrows the cause more than how it looks today."
          >
            <Fieldset legend="How did it start?">
              <ChoiceGroup
                value={history.onset}
                onChange={(v) => setH("onset", v)}
                options={[
                  { value: "gradual", label: "Gradually" },
                  { value: "sudden", label: "Suddenly" },
                  { value: "unsure", label: "Not sure" },
                ]}
              />
            </Fieldset>

            <Fieldset legend="Where do you notice it?">
              <ChoiceGroup
                value={history.pattern}
                onChange={(v) => setH("pattern", v)}
                options={[
                  { value: "receding", label: "Receding hairline" },
                  { value: "crown", label: "Crown" },
                  { value: "diffuse", label: "All over" },
                  { value: "patchy", label: "In patches" },
                  { value: "unsure", label: "Not sure" },
                ]}
              />
            </Fieldset>

            <Fieldset legend="How long has it been going on?">
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="number"
                  min={0}
                  value={history.duration_months ?? ""}
                  onChange={(e) =>
                    setH("duration_months", e.target.value === "" ? null : Number(e.target.value))
                  }
                  className="w-24 rounded border bg-surface px-3 py-2"
                />
                <span className="text-ink-soft">months</span>
              </label>
            </Fieldset>

            <Fieldset legend="Family history">
              <CheckRow
                label="Hair loss runs in my family"
                checked={history.family_history_hair_loss}
                onChange={(v) => setH("family_history_hair_loss", v)}
              />
              {history.family_history_hair_loss && (
                <ChoiceGroup
                  value={history.family_history_side}
                  onChange={(v) => setH("family_history_side", v)}
                  options={[
                    { value: "maternal", label: "Mother's side" },
                    { value: "paternal", label: "Father's side" },
                    { value: "both", label: "Both" },
                    { value: "unsure", label: "Not sure" },
                  ]}
                />
              )}
            </Fieldset>
          </StepPanel>
        )}

        {step === "health" && (
          <StepPanel
            title="Health context"
            intro="These are the causes a camera will never find. Several of them are treatable, which is exactly why they are worth catching."
          >
            <Fieldset
              legend="Conditions"
              hint="Any of these can cause hair loss on its own."
            >
              {(
                [
                  ["thyroid_condition", "Thyroid condition"],
                  ["iron_deficiency", "Iron deficiency or anaemia"],
                  ["autoimmune_condition", "An autoimmune condition"],
                  ["pcos", "PCOS"],
                  ["scalp_condition", "A diagnosed scalp condition"],
                ] as const
              ).map(([key, label]) => (
                <CheckRow
                  key={key}
                  label={label}
                  checked={history[key] as boolean}
                  onChange={(v) => setH(key, v as never)}
                />
              ))}
            </Fieldset>

            <Fieldset
              legend="In the last year"
              hint="Shedding often begins two to four months after one of these."
            >
              {(
                [
                  ["recent_illness", "A significant illness"],
                  ["recent_surgery", "Surgery"],
                  ["major_stress", "A period of major stress"],
                  ["rapid_weight_loss", "Rapid weight loss"],
                  ["postpartum", "Childbirth"],
                ] as const
              ).map(([key, label]) => (
                <CheckRow
                  key={key}
                  label={label}
                  checked={history[key] as boolean}
                  onChange={(v) => setH(key, v as never)}
                />
              ))}
            </Fieldset>

            <Fieldset
              legend="Medications"
              hint="Anything you take regularly. Some are associated with shedding — worth raising with your prescriber, never a reason to stop on your own."
            >
              <div className="flex flex-wrap gap-1.5">
                {history.medications.map((m) => (
                  <span key={m} className="inline-flex items-center gap-1.5 rounded border px-2.5 py-1 text-sm">
                    {m}
                    <button
                      onClick={() =>
                        setH("medications", history.medications.filter((x) => x !== m))
                      }
                      aria-label={`Remove ${m}`}
                      className="text-ink-faint hover:text-ink"
                    >
                      ×
                    </button>
                  </span>
                ))}
              </div>
              <div className="flex gap-2">
                <input
                  value={medInput}
                  onChange={(e) => setMedInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      const name = medInput.trim();
                      if (name && !history.medications.includes(name)) {
                        setH("medications", [...history.medications, name]);
                        setMedInput("");
                      }
                    }
                  }}
                  placeholder="e.g. levothyroxine"
                  className="flex-1 rounded border bg-surface px-3 py-2 text-sm"
                />
              </div>
            </Fieldset>

            <Fieldset legend="Hair care">
              {(
                [
                  ["tight_hairstyles", "Tight braids, weaves, or ponytails"],
                  ["chemical_treatments", "Relaxers, bleach, or perms"],
                  ["heat_styling", "Frequent heat styling"],
                ] as const
              ).map(([key, label]) => (
                <CheckRow
                  key={key}
                  label={label}
                  checked={history[key] as boolean}
                  onChange={(v) => setH(key, v as never)}
                />
              ))}
            </Fieldset>
          </StepPanel>
        )}

        {step === "safety" && (
          <StepPanel
            title="Safety check"
            intro="A handful of signs that a photograph cannot show. Ticking any one of them routes you to a clinician instead of a routine."
          >
            <SymptomCheck
              domain="hair"
              hair={hairSymptoms}
              skin={skinSymptoms}
              onHairChange={setHairSymptoms}
              onSkinChange={() => {}}
            />
            <div className="border-t pt-4">
              <CheckRow
                label="I also have a painful or tender scalp"
                checked={history.scalp_pain}
                onChange={(v) => setH("scalp_pain", v)}
              />
              <CheckRow
                label="My scalp is itchy"
                checked={history.scalp_itch}
                onChange={(v) => setH("scalp_itch", v)}
              />
            </div>
          </StepPanel>
        )}

        {step === "capture" && (
          <StepPanel
            title="Seven views"
            intro="Each photo passes a quality check before anything is analysed. If you've scanned before, your previous shot appears as a guide so the two stay comparable."
          >
            <GuidedCapture
              domain="hair"
              presetSymptoms={hairSymptoms}
              onComplete={(sessionId) => router.push(`/scan/${sessionId}/result`)}
            />
          </StepPanel>
        )}

        {/* Navigation. Capture manages its own advance, so it opts out. */}
        {step !== "capture" && step !== "reading" && (
          <div className="mt-8 flex items-center justify-between border-t pt-5">
            <Button variant="ghost" onClick={back} disabled={index === 0}>
              <ArrowLeft className="h-4 w-4" /> Back
            </Button>
            <div className="flex items-center gap-3">
              <Link href="/" className="text-sm text-ink-faint underline-offset-4 hover:underline">
                Save and exit
              </Link>
              <Button onClick={next} disabled={saving}>
                {saving ? "Saving…" : "Continue"}
                <ArrowRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

const AGE_BANDS = ["Under 25", "25–34", "35–44", "45–54", "55–64", "65+"];

/** Age is stored as a year but only ever collected and reported as a band. */
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
