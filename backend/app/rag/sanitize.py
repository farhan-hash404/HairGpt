"""Text hygiene shared by the corpus builder and the query guardrails.

Scraped text ends up inside a language model's context window, which makes it
an attack surface: a page containing "ignore previous instructions" is an
indirect prompt injection. Authoritative health sites are unlikely to carry one,
but the corpus is filtered anyway — defence in depth costs nothing, and the same
detector screens user questions before they reach retrieval.
"""

from __future__ import annotations

import re
import unicodedata

_ZERO_WIDTH = dict.fromkeys(map(ord, "​‌‍⁠﻿"), None)
# Numbered markers like [12] or [3-5], and the empty brackets left behind when a
# JATS <xref> element is removed from "... after childbirth [<xref>12</xref>]".
_CITATION_MARKERS = re.compile(r"\s*\[(?:\d+(?:\s*[-–,;]\s*\d+)*|[\s,;–-]*)\]")
_WHITESPACE = re.compile(r"[ \t\r\f\v]+")

INJECTION_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\bignore\s+(?:all\s+|any\s+|the\s+)?(?:previous|prior|above|earlier)\s+(?:instructions?|prompts?|rules?)",
        r"\b(?:disregard|forget|override)\s+(?:all\s+|any\s+|the\s+|your\s+)?(?:previous|prior|above|earlier|system)\s+(?:instructions?|context|rules?|prompts?)",
        r"\byou\s+are\s+(?:now\s+)?(?:chatgpt|dan|an?\s+unrestricted|in\s+developer\s+mode)",
        r"\b(?:reveal|print|show|repeat)\s+(?:me\s+)?(?:your|the)\s+(?:system\s+)?(?:prompt|instructions)",
        r"\bsystem\s+prompt\b",
        r"\bdo\s+anything\s+now\b",
        r"\bjailbreak\b",
        r"</?\s*(?:system|assistant|instructions?)\s*>",
        r"\bnew\s+instructions?\s*:",
        r"\bact\s+as\s+(?:a\s+)?(?:doctor|physician|pharmacist)\s+and\s+(?:prescribe|diagnose)",
    )
]


def normalize(text: str) -> str:
    """Unicode-normalise, strip zero-width characters and collapse whitespace."""
    text = unicodedata.normalize("NFKC", text).translate(_ZERO_WIDTH)
    text = _WHITESPACE.sub(" ", text)
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())


def strip_citation_markers(text: str) -> str:
    """Remove bracketed reference numbers like [12] or [3-5] from article prose."""
    return _CITATION_MARKERS.sub("", text)


def looks_like_injection(text: str) -> bool:
    return any(p.search(text) for p in INJECTION_PATTERNS)


_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(])")


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_SPLIT.split(text) if s.strip()]


def drop_injection_sentences(text: str) -> tuple[str, int]:
    """Remove any sentence that reads like an instruction to a language model.

    Returns (clean_text, number_of_sentences_removed).
    """
    kept, removed = [], 0
    for sentence in split_sentences(text):
        if looks_like_injection(sentence):
            removed += 1
            continue
        kept.append(sentence)
    return " ".join(kept), removed
