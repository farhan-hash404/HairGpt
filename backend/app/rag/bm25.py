"""Sparse retrieval: BM25 over a normalised, lightly stemmed vocabulary.

Dense embeddings capture meaning; BM25 captures exact clinical terms that
embedding models blur ("dutasteride" vs "finasteride", "LPP" vs "FFA"). The
hybrid retriever fuses both.

The tokenizer does three things a naive split would not:

* British -> American spelling. The NHS writes "anaemia" and "seborrhoeic";
  PubMed mostly writes "anemia" and "seborrheic". Without normalising both
  sides, lexical search silently misses half the corpus.
* Stop-word removal and light suffix stemming ("thinning" ~ "thin").
* Lay-term expansion on the query side only ("baldness" also searches
  "alopecia"), so people are not penalised for not knowing clinical vocabulary.
"""

from __future__ import annotations

import re
import unicodedata

from rank_bm25 import BM25Okapi

_BRITISH = [
    (re.compile(r"aem"), "em"),  # anaemia, haemoglobin
    (re.compile(r"oedem"), "edem"),  # oedema
    (re.compile(r"oestr"), "estr"),  # oestrogen
    (re.compile(r"paed"), "ped"),  # paediatric
    (re.compile(r"seborrhoe"), "seborrhe"),
    (re.compile(r"diarrhoe"), "diarrhe"),
    (re.compile(r"our\b"), "or"),  # colour, tumour, behaviour
    (re.compile(r"ise\b"), "ize"),  # recognise
    (re.compile(r"isation\b"), "ization"),
]

STOPWORDS = frozenset(
    """a about above after again against all am an and any are as at be because been before being
    below between both but by can could did do does doing down during each few for from further had
    has have having he her here hers him his how i if in into is it its itself just me more most my
    no nor not now of off on once only or other our out over own same she should so some such than
    that the their them then there these they this those through to too under until up very was we
    were what when where which while who whom why will with would you your yours may might also
    get got use used using"""
    .split()
)

# Lay term -> clinical terms, expanded on the QUERY side only.
SYNONYMS = {
    "bald": ["alopecia"],
    "baldness": ["alopecia", "androgenetic"],
    "balding": ["alopecia", "androgenetic"],
    "thinning": ["alopecia", "hair", "loss"],
    "shedding": ["effluvium", "telogen"],
    "dandruff": ["seborrheic", "dermatitis", "malassezia"],
    "ringworm": ["tinea", "capitis"],
    "flaky": ["dandruff", "seborrheic"],
    "patches": ["areata", "patchy"],
    "patchy": ["areata"],
    "rogaine": ["minoxidil"],
    "propecia": ["finasteride"],
    "thyroid": ["hypothyroidism"],
    "anemia": ["iron", "ferritin"],
    "scarring": ["cicatricial"],
    "follicles": ["follicle"],
}

_TOKEN = re.compile(r"[a-z0-9]+")


def _stem(tok: str) -> str:
    if len(tok) <= 4 or tok.isdigit():
        return tok
    for suffix, repl in (("ies", "y"), ("sses", "ss"), ("ing", ""), ("edly", ""), ("ed", ""), ("es", ""), ("s", "")):
        if tok.endswith(suffix) and not tok.endswith("ss") and len(tok) - len(suffix) >= 4:
            return tok[: -len(suffix)] + repl
    return tok


def normalize_spelling(token: str) -> str:
    for pattern, repl in _BRITISH:
        token = pattern.sub(repl, token)
    return token


def _raw_tokens(text: str) -> list[str]:
    # Stop-words are dropped BEFORE spelling normalisation, otherwise "your"
    # would become "yor" and slip past the stop-word list.
    lowered = unicodedata.normalize("NFKC", text).lower()
    return [normalize_spelling(t) for t in _TOKEN.findall(lowered) if t not in STOPWORDS]


def tokenize(text: str) -> list[str]:
    return [_stem(t) for t in _raw_tokens(text)]


def tokenize_query(text: str) -> list[str]:
    base = _raw_tokens(text)
    expanded = list(base)
    for tok in base:
        expanded.extend(SYNONYMS.get(tok, []))
    return [_stem(t) for t in expanded]


class BM25Index:
    def __init__(self, ids: list[str], texts: list[str], k1: float = 1.4, b: float = 0.72):
        self.ids = ids
        corpus = [tokenize(t) or ["_empty_"] for t in texts]
        self._bm25 = BM25Okapi(corpus, k1=k1, b=b)

    def search(self, query: str, k: int, allowed: set[str] | None = None) -> list[tuple[str, float]]:
        tokens = tokenize_query(query)
        if not tokens:
            return []
        scores = self._bm25.get_scores(tokens)
        ranked = sorted(
            ((self.ids[i], float(s)) for i, s in enumerate(scores) if s > 0),
            key=lambda pair: pair[1],
            reverse=True,
        )
        if allowed is not None:
            ranked = [pair for pair in ranked if pair[0] in allowed]
        return ranked[:k]
