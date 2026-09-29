"""Deterministic citation auditing — the non-LLM half of the hallucination gate.

An LLM judging another LLM shares its blind spots, so the first line of
defence is mechanical. Given an answer with inline citations like [2] and the
numbered passages it was allowed to use, the auditor fails the answer if:

  * it cites a source number that was never provided   (fabricated citation)
  * a cited sentence is not supported by the passage it cites
  * a sentence contains a number absent from its cited passages
                                                         (fabricated statistic)
  * a sentence names a drug its cited passages never mention
                                                         (invented treatment)
  * a factual-looking sentence carries no citation at all
  * it states a dose, a diagnosis, or a prescription directive

The report doubles as revision feedback: the agent regenerates once with the
specific failures listed, and falls back to a verbatim extractive answer if
the second attempt fails too.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.rag.bm25 import tokenize
from app.rag.sanitize import split_sentences

_CITATION = re.compile(r"\[(\d+)(?:\s*,\s*(\d+))*\]")
_ALL_CITATION_NUMBERS = re.compile(r"\d+")
_NUMBER = re.compile(r"(?<![\w.])(\d+(?:[.,]\d+)*)(\s?%)?")

# Drugs and treatments that must never appear in an answer unless a cited
# passage names them.
DRUG_TERMS = (
    "minoxidil", "finasteride", "dutasteride", "spironolactone", "ketoconazole", "zinc pyrithione",
    "selenium sulfide", "ciclopirox", "baricitinib", "ritlecitinib", "tofacitinib", "ruxolitinib",
    "deuruxolitinib", "corticosteroid", "prednisolone", "triamcinolone", "clobetasol", "betamethasone",
    "hydroxychloroquine", "doxycycline", "isotretinoin", "tretinoin", "bimatoprost", "latanoprost",
    "platelet-rich plasma", "prp", "anthralin", "diphenylcyclopropenone", "cyclosporine", "methotrexate",
    "terbinafine", "griseofulvin", "itraconazole", "biotin", "iron supplement", "vitamin d",
)

# Signals that a sentence asserts a medical fact and therefore needs a source.
_CLAIM_SIGNALS = re.compile(
    r"\d|\b(caus|treat|cure|effective|efficac|improv|reduc|increas|risk|associat|linked|"
    r"trigger|result|lead|prevent|work|regrow|stop|side effect|common|rare|usually|often)",
    re.IGNORECASE,
)
# Sentences that are advice to seek help, or statements about the app itself,
# carry no clinical claim and need no citation.
_EXEMPT = re.compile(
    r"\b(gp|doctor|clinician|pharmacist|dermatologist|prescriber|healthcare professional)\b|"
    r"\bhairgpt\b|\bnot (a )?diagnos|\bi (could not|couldn't|can't|cannot|don't|do not)\b|"
    r"\bsources? (do not|don't|does not|doesn't)\b|general information",
    re.IGNORECASE,
)

POLICY_PATTERNS = {
    "dosing": re.compile(
        r"\b(take|apply|use|inject|dose|rub)\b[^.]{0,40}?\b(\d+(\.\d+)?\s?(mg|mcg|µg|ml|millilit|g)\b|"
        r"once|twice|\d+\s*times)"
        r"|\b\d+(\.\d+)?\s?(mg|mcg|µg)\s?(/|per\s)\s?(day|d|kg)\b"
        r"|\b\d+(\.\d+)?\s?(mg|mcg|µg)\b[^.]{0,30}\b(daily|a day|per day|twice|once)",
        re.IGNORECASE,
    ),
    "diagnosis": re.compile(
        r"\byou (definitely |probably |likely )?(have|'ve got|are suffering from)\s+"
        r"(alopecia|androgenetic|telogen|tinea|ringworm|psoriasis|lichen|seborrh|cancer|melanoma)"
        r"|\b(this|it) is (definitely|certainly|clearly)\b",
        re.IGNORECASE,
    ),
    "prescription_directive": re.compile(
        r"\byou should (take|start|use|begin)\b[^.]{0,40}\b(finasteride|dutasteride|spironolactone|"
        r"oral minoxidil|baricitinib|ritlecitinib|isotretinoin)\b"
        r"|\b(start|begin) (taking )?(finasteride|dutasteride|spironolactone|baricitinib|ritlecitinib)\b",
        re.IGNORECASE,
    ),
}


@dataclass
class SentenceCheck:
    sentence: str
    citations: list[int]
    supported: bool
    reason: str = ""
    overlap: float = 0.0


@dataclass
class AuditReport:
    passed: bool
    checks: list[SentenceCheck] = field(default_factory=list)
    fabricated_citations: list[int] = field(default_factory=list)
    unsupported: list[str] = field(default_factory=list)
    uncited_claims: list[str] = field(default_factory=list)
    unmatched_numbers: list[str] = field(default_factory=list)
    unmatched_terms: list[str] = field(default_factory=list)
    policy_violations: list[str] = field(default_factory=list)

    @property
    def support_ratio(self) -> float:
        cited = [c for c in self.checks if c.citations]
        return round(sum(c.supported for c in cited) / len(cited), 3) if cited else 0.0

    def feedback(self) -> str:
        """Specific, actionable problems for a revision prompt."""
        lines = []
        if self.fabricated_citations:
            lines.append(f"You cited sources that do not exist: {self.fabricated_citations}. Use only the numbered sources.")
        for s in self.unsupported[:4]:
            lines.append(f"Not supported by the source it cites: \"{s}\"")
        for s in self.uncited_claims[:4]:
            lines.append(f"This factual claim has no citation: \"{s}\"")
        if self.unmatched_numbers:
            lines.append(f"These numbers do not appear in the cited sources: {self.unmatched_numbers}")
        if self.unmatched_terms:
            lines.append(f"These treatments are not mentioned by the cited sources: {self.unmatched_terms}")
        for v in self.policy_violations:
            lines.append(f"Policy violation ({v}). Never state doses, diagnose, or direct anyone to a prescription drug.")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "support_ratio": self.support_ratio,
            "fabricated_citations": self.fabricated_citations,
            "unsupported": self.unsupported,
            "uncited_claims": self.uncited_claims,
            "unmatched_numbers": self.unmatched_numbers,
            "unmatched_terms": self.unmatched_terms,
            "policy_violations": self.policy_violations,
        }


def _numbers(text: str) -> set[str]:
    return {m.group(1).replace(",", "") for m in _NUMBER.finditer(text)}


def _terms(text: str) -> set[str]:
    low = text.lower()
    return {t for t in DRUG_TERMS if re.search(rf"\b{re.escape(t)}\b", low)}


def _citations_in(sentence: str) -> list[int]:
    found: list[int] = []
    for match in _CITATION.finditer(sentence):
        found.extend(int(n) for n in _ALL_CITATION_NUMBERS.findall(match.group(0)))
    return found


def policy_violations(text: str) -> list[str]:
    return [name for name, pattern in POLICY_PATTERNS.items() if pattern.search(text)]


def audit(answer: str, sources: dict[int, str], min_overlap: float = 0.5) -> AuditReport:
    """Audit an answer against the numbered source passages it was given."""
    report = AuditReport(passed=True)
    report.policy_violations = policy_violations(answer)

    # Lines first: a bullet or heading must not merge with the sentence below it
    # and borrow that sentence's citation (or lose its own).
    for raw in (s for line in answer.splitlines() for s in split_sentences(line)):
        citations = _citations_in(raw)
        sentence = _CITATION.sub("", raw).strip()
        if len(sentence.split()) < 3:
            continue
        check = SentenceCheck(sentence=sentence, citations=citations, supported=True)

        if not citations:
            if _CLAIM_SIGNALS.search(sentence) and not _EXEMPT.search(sentence):
                check.supported = False
                check.reason = "uncited claim"
                report.uncited_claims.append(sentence)
            report.checks.append(check)
            continue

        bad = [n for n in citations if n not in sources]
        if bad:
            report.fabricated_citations.extend(bad)
        cited_text = " ".join(sources[n] for n in citations if n in sources)
        if not cited_text:
            check.supported = False
            check.reason = "cites only non-existent sources"
            report.unsupported.append(sentence)
            report.checks.append(check)
            continue

        sentence_tokens = set(tokenize(sentence))
        source_tokens = set(tokenize(cited_text))
        check.overlap = round(len(sentence_tokens & source_tokens) / max(len(sentence_tokens), 1), 3)
        if check.overlap < min_overlap:
            check.supported = False
            check.reason = f"low overlap with cited source ({check.overlap:.2f})"
            report.unsupported.append(sentence)

        missing_numbers = sorted(_numbers(sentence) - _numbers(cited_text))
        if missing_numbers:
            check.supported = False
            check.reason = "number not in cited source"
            report.unmatched_numbers.extend(missing_numbers)
        missing_terms = sorted(_terms(sentence) - _terms(cited_text))
        if missing_terms:
            check.supported = False
            check.reason = "treatment not in cited source"
            report.unmatched_terms.extend(missing_terms)
        report.checks.append(check)

    report.fabricated_citations = sorted(set(report.fabricated_citations))
    report.passed = not (
        report.fabricated_citations or report.unsupported or report.uncited_claims
        or report.unmatched_numbers or report.unmatched_terms or report.policy_violations
    )
    return report
