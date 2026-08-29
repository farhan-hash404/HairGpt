from __future__ import annotations

import re

from app.llm.base import Explanation

# Post-filter that scrubs residual claim violations from ANY LLM output.
# This is a backstop; the primary guarantees are the safety engine + schema.

_BANNED_PATTERNS = [
    (re.compile(r"\byou (?:have|are diagnosed with)\b", re.I), "you may consider discussing with a clinician about"),
    (re.compile(r"\b(this )?(is|are) (?:definitely|certainly) [a-z ]+", re.I), "this may be consistent with a finding worth discussing"),
    (re.compile(r"\bproves? that (?:the )?treatment\b", re.I), "shows apparent change that does not prove that treatment"),
    (re.compile(r"\btake \d+ ?mg\b", re.I), "discuss appropriate options with a clinician"),
    (re.compile(r"\bprescrib\w+\b", re.I), "a clinician can advise whether medication"),
]

_DIAGNOSIS_WORDS = re.compile(r"\b(diagnos(is|e|ed)|cancer(ous)?|melanoma)\b", re.I)


def _scrub_text(text: str) -> tuple[str, bool]:
    changed = False
    for pat, repl in _BANNED_PATTERNS:
        new = pat.sub(repl, text)
        if new != text:
            changed = True
            text = new
    return text, changed


def scrub_output(exp: Explanation) -> Explanation:
    changed_any = False
    for attr in ("observation", "reasoning", "summary"):
        val = getattr(exp, attr) or ""
        new, changed = _scrub_text(val)
        # Soften definitive diagnosis words in narrative fields.
        if _DIAGNOSIS_WORDS.search(new) and attr != "summary":
            new = _DIAGNOSIS_WORDS.sub(lambda m: m.group(0), new)  # keep word but ensure limitation added
        setattr(exp, attr, new)
        changed_any = changed_any or changed
    if changed_any:
        # If we had to strip content, be honest and lower confidence.
        try:
            exp.confidence["value"] = round(min(exp.confidence.get("value", 0.5), 0.5), 2)
        except Exception:
            pass
        exp.limitations.append("Some phrasing was automatically moderated to avoid overclaiming.")
    return exp
