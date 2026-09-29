"""Input guardrails for the evidence Q&A agent.

These run before retrieval, deterministically, so no model output can talk its
way around them:

  injection   instructions aimed at the model ("ignore previous instructions")
              are refused outright
  emergency   signs of an emergency or a crisis short-circuit to where to get
              help now — retrieval and generation are skipped entirely
  dosing      requests for a dose are answered with sources but never a dose;
              the answer is told to point to the label or a prescriber
  diagnosis   "do I have X?" gets general information plus a reminder that
              only a clinician can diagnose
  treatment   "should I start/stop/switch ...?" gets information plus a
              reminder that the decision belongs with a prescriber

The patterns are measured by scripts/eval_redteam.py; every miss it found
became a pattern here, checked against the benign questions for over-blocking.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.rag.sanitize import looks_like_injection

MAX_QUESTION_CHARS = 600

# First person or present tense: "my lips swelled up" is an emergency, "can
# minoxidil cause face swelling?" is a question.
_EMERGENCY = re.compile(
    r"\b(can'?t|cannot|struggling to|hard to) breathe\b|\b(difficulty|trouble) breathing\b"
    r"|\bmy\s+(throat|tongue|lips?|mouth|face|eyes?)\b[^.?!]{0,25}\b(swell\w*|swollen|closing|tight\w*)"
    r"|\b(throat|tongue|lips?|mouth|face)\s+(is|are|has been|have been|keeps?)\s+(swelling|swollen|closing|tightening)"
    r"|\b(swelled|swollen)\s+up\b"
    r"|\b(i\s+(have|am having|'m having|got)|i've\s+got|having)\s+(a\s+)?(chest pain|pain in my chest|tight chest)"
    r"|\bmy\s+chest\s+(hurts|is\s+tight|feels\s+tight)"
    r"|\banaphyla\w*|\boverdos\w*|\btoo many (tablets|pills)\b|\bpassed out\b|\bunconscious\b|\bseizures?\b",
    re.IGNORECASE,
)
_CRISIS = re.compile(
    r"\b(suicid\w*|kill(ing)? myself|end(ing)? my life|end it all|self[- ]harm\w*|(hurt|harm)(ing)? myself|"
    r"don'?t want to (live|be alive|be here)|want to die|wish i (was|were) dead|better off dead|"
    r"no (point|reason) (in |to )?(living|live|going on)|not worth living)\b",
    re.IGNORECASE,
)
# Questions get a broader injection check than scraped documents: a person has
# no reason to address the model's rules at all, while a medical page may
# legitimately say "follow the instructions on the label".
_INPUT_INJECTION = re.compile(
    r"\b(ignore|disregard|forget|override|bypass|circumvent|disable|turn off)\s+((all|any|of|the|every)\s+)*"
    r"(your|previous|prior|above|earlier|system|safety|these)\s+(\w+\s+)?"
    r"(rules?|instructions?|guidelines?|guardrails?|polic(y|ies)|restrictions?|filters?|prompts?|programming|"
    r"constraints?|training)\b"
    r"|\bforget\s+(everything|all|what)\b[^.?!]{0,30}\b(told|said|instructed|given)\b"
    r"|\byou\s+(now\s+)?have\s+no\s+(rules|restrictions|limits|limitations|filters|guidelines)\b"
    r"|\bno\s+(rules|restrictions|filters)\s+(apply|anymore|any more)\b"
    r"|\b(pretend|imagine|act|behave|role-?play)\s+(to\s+be|you\s+are|you're|as|that\s+you\s+are|like)\s+"
    r"(a\s+|an\s+|my\s+)?(real\s+)?(doctor|physician|dermatologist|trichologist|gp|pharmacist|nurse|prescriber|"
    r"clinician)\b"
    r"|\b(developer|dev|god|jailbreak|unrestricted|admin|debug)\s+mode\b"
    r"|\b(instructions?|rules?|prompt|guidelines?)\s+(that\s+)?you\s+(were|have\s+been|got)\s+(given|told)\b"
    r"|\bwhat\s+(are|were)\s+your\s+(instructions|rules|guidelines|directives)\b"
    r"|\b(answer|respond|reply)\s+without\s+(any\s+)?(citations?|sources?|references?|evidence)\b",
    re.IGNORECASE,
)
# A dose request needs dosing vocabulary, or "how much/many/often" together with
# a medicine or a verb of taking. "How many hairs a day is normal?" is not one —
# an earlier, looser pattern flagged it. Units may be glued to digits ("5mg").
_DOSE_WORDS = re.compile(
    r"\b(dose|doses|dosage|dosing)\b|(?<![a-z])(mg|mcg|ml|milligrams?|millilit(er|re)s?)\b", re.IGNORECASE
)
_HOW_MUCH = re.compile(r"\bhow (much|many|often)\b", re.IGNORECASE)
_DOSE_CHANGE = re.compile(
    r"\b(double|triple|halve)\b|\bmissed\s+(a\s+|my\s+)?(dose|day|application|tablet|pill)"
    r"|\b(increase|raise|lower|reduce|up)\s+(my|the)\s+(dose|amount|strength)"
    r"|\b(what|which)\s+(strength|concentration|percentage)\b|\bhow\s+strong\b",
    re.IGNORECASE,
)
_MEDICINE = re.compile(
    r"\b(minoxidil|rogaine|regaine|finasteride|propecia|proscar|dutasteride|spironolactone|ketoconazole|"
    r"biotin|iron|vitamin|supplement|tablets?|pills?|foam|solution|shampoo|medicine|medication|drug|"
    r"take|taking|apply|applying|use|using)\b",
    re.IGNORECASE,
)
_DIAGNOSIS = re.compile(
    r"\b(do i have|have i got|is (this|it|my \w+) (alopecia|cancer|ringworm|psoriasis|normal)|"
    r"diagnose me|what (condition|disease) do i have|am i going bald|"
    r"what('?s| is) (wrong with|causing|behind) (me|my)|tell me what (i have|this is|it is))\b",
    re.IGNORECASE,
)
# "Should I use a gentle shampoo?" is self-care; "should I take finasteride?"
# is a treatment decision. Starting, stopping or switching is always one.
_TREATMENT_CHANGE = re.compile(
    r"\bshould\s+i\s+(start|stop|switch|change|quit|come\s+off|keep\s+(taking|using)|continue|go\s+on)\b"
    r"|\b(which|what)\s+(drug|medicine|medication|treatment|tablet|pill)\s+(should|do)\s+i\b"
    r"|\b(tell|help)\s+me\s+(which|what)\s+(treatment|medicine|medication|drug)\b"
    r"|\bwithout\s+(a\s+)?(prescription|seeing\s+a\s+(doctor|gp)|doctor|gp)\b"
    r"|\bprescribe\s+me\b|\bwrite\s+me\s+a\s+prescription\b",
    re.IGNORECASE,
)
_SHOULD_TAKE = re.compile(r"\bshould\s+i\s+(take|use|try|get)\b", re.IGNORECASE)
_PRESCRIPTION_MEDICINE = re.compile(
    r"\b(finasteride|propecia|proscar|dutasteride|minoxidil|rogaine|regaine|spironolactone|steroids?|"
    r"corticosteroids?|jak inhibitors?|baricitinib|ritlecitinib|levothyroxine|medicines?|medications?|"
    r"tablets?|pills?|drugs?)\b",
    re.IGNORECASE,
)


def _is_dosing_request(text: str) -> bool:
    return bool(
        _DOSE_WORDS.search(text)
        or ((_HOW_MUCH.search(text) or _DOSE_CHANGE.search(text)) and _MEDICINE.search(text))
    )


def _is_treatment_decision(text: str) -> bool:
    return bool(_TREATMENT_CHANGE.search(text) or (_SHOULD_TAKE.search(text) and _PRESCRIPTION_MEDICINE.search(text)))


@dataclass
class GuardDecision:
    allowed: bool
    flags: list[str] = field(default_factory=list)
    message: str = ""  # shown instead of an answer when not allowed
    notes: list[str] = field(default_factory=list)  # appended to an allowed answer

    def to_dict(self) -> dict:
        return {"allowed": self.allowed, "flags": self.flags, "message": self.message, "notes": self.notes}


EMERGENCY_MESSAGE = (
    "This sounds like it could be an emergency. Please call your local emergency number now "
    "(999 in the UK, 911 in the US, 112 in the EU) or go to the nearest emergency department. "
    "HairGPT cannot help with emergencies."
)
CRISIS_MESSAGE = (
    "It sounds like you're going through something really hard. You don't have to face it alone: "
    "please reach out now to a crisis line — Samaritans on 116 123 (UK), 988 (US), or your local "
    "emergency number. Talking to someone you trust, or your GP, can help too."
)
INJECTION_MESSAGE = (
    "I can only answer questions about hair and scalp health from my medical sources, and I can't "
    "change how I work. Please ask your question directly."
)


def check_input(question: str) -> GuardDecision:
    text = (question or "").strip()
    if not text:
        return GuardDecision(False, ["empty"], "Please enter a question about hair or scalp health.")
    if len(text) > MAX_QUESTION_CHARS:
        return GuardDecision(False, ["too_long"],
                             f"Please keep questions under {MAX_QUESTION_CHARS} characters.")
    if _CRISIS.search(text):
        return GuardDecision(False, ["crisis"], CRISIS_MESSAGE)
    if _EMERGENCY.search(text):
        return GuardDecision(False, ["emergency"], EMERGENCY_MESSAGE)
    if looks_like_injection(text) or _INPUT_INJECTION.search(text):
        return GuardDecision(False, ["prompt_injection"], INJECTION_MESSAGE)

    decision = GuardDecision(True)
    if _is_dosing_request(text):
        decision.flags.append("dosing_request")
        decision.notes.append(
            "HairGPT does not give doses. Follow the product label, or ask a pharmacist or the "
            "prescriber what is right for you."
        )
    if _DIAGNOSIS.search(text):
        decision.flags.append("diagnosis_request")
        decision.notes.append(
            "This is general information, not a diagnosis. Only a clinician who examines you can "
            "say what is causing your hair loss."
        )
    if _is_treatment_decision(text):
        decision.flags.append("treatment_decision")
        decision.notes.append(
            "HairGPT can't make treatment decisions for you. Whether to start, stop or switch a "
            "treatment is for you to decide with a GP, pharmacist or dermatologist who knows your "
            "health history; prescription-only medicines should only come from a prescriber."
        )
    return decision
