"""Registry of the medical sources HairGPT is allowed to learn from.

Two rules decide what goes in here:

1. **Authority.** National health services, national libraries of medicine,
   federal research institutes, drug-label registries, and peer-reviewed
   literature. Social media, forums, blogs and marketing copy are never sources.
2. **Licence.** The corpus is committed to a public repository and quoted back
   to users, so every source must permit reuse and redistribution. That rules
   out otherwise-excellent but all-rights-reserved publishers (AAD, DermNet NZ),
   and it is why peer-reviewed articles are restricted to CC BY / CC0.

Each document the scraper produces carries its licence and attribution, and the
UI shows them alongside every citation.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Grades order evidence for reranking and are shown to the user as provenance.
EVIDENCE_GRADES = {
    "systematic_review": 1.0,  # systematic reviews / meta-analyses
    "clinical_guideline": 0.95,  # national clinical guidance
    "regulatory_label": 0.9,  # official drug labelling (DailyMed / FDA)
    "patient_guideline": 0.85,  # national patient information (NHS, NIH, NLM)
    "narrative_review": 0.75,  # peer-reviewed narrative reviews
    "primary_study": 0.65,  # individual peer-reviewed studies
}


@dataclass(frozen=True)
class License:
    spdx: str
    url: str
    attribution: str
    redistributable: bool = True


OGL_3 = License(
    spdx="OGL-UK-3.0",
    url="https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/",
    attribution="Contains public sector information licensed under the Open Government Licence v3.0.",
)
US_GOV_PD = License(
    spdx="US-Government-Public-Domain",
    url="https://www.nlm.nih.gov/web_policies.html",
    attribution="Produced by a US federal agency; not subject to copyright in the United States.",
)
CC_BY = License(
    spdx="CC-BY-4.0",
    url="https://creativecommons.org/licenses/by/4.0/",
    attribution="Licensed under Creative Commons Attribution.",
)
CC0 = License(
    spdx="CC0-1.0",
    url="https://creativecommons.org/publicdomain/zero/1.0/",
    attribution="Dedicated to the public domain under CC0.",
)

# Europe PMC licence strings that permit redistribution of verbatim excerpts.
# Non-commercial and no-derivatives variants are deliberately excluded.
EUROPEPMC_ALLOWED_LICENSES = {"cc by": CC_BY, "cc0": CC0, "cc by-sa": CC_BY}


@dataclass(frozen=True)
class WebPage:
    """A single HTML page from an allowlisted publisher."""

    source: str  # registry key, e.g. "NHS"
    slug: str
    url: str
    domain: str = "hair"  # hair | skin | both


@dataclass(frozen=True)
class Publisher:
    key: str
    name: str
    license: License
    evidence_grade: str
    # CSS selector for the main article content on this publisher's pages.
    content_selector: str
    # Section headings to drop: navigation, references, and — deliberately —
    # dosing instructions. HairGPT never states a dose, so the corpus should not
    # hand the language model one to repeat.
    drop_headings: tuple[str, ...] = field(default_factory=tuple)


PUBLISHERS: dict[str, Publisher] = {
    "NHS": Publisher(
        key="NHS",
        name="NHS (National Health Service, England)",
        license=OGL_3,
        evidence_grade="patient_guideline",
        content_selector=".nhsuk-grid-column-two-thirds",
        drop_headings=(
            "how and when to take", "how to take", "dosage", "how much to take",
            "if you forget", "if you take too much", "further information",
            "emotional help",
        ),
    ),
    "MEDLINEPLUS": Publisher(
        key="MEDLINEPLUS",
        name="MedlinePlus (US National Library of Medicine)",
        license=US_GOV_PD,
        evidence_grade="patient_guideline",
        content_selector="#topic-summary, .main .mp-exp",
        drop_headings=(
            "additional information", "references", "clinical trials", "scientific articles",
            "other names", "related health topics", "understanding genetics",
            "disclaimers", "patient support", "genetic and rare diseases",
            "catalog of genes", "medical encyclopedia", "learn more about the gene",
        ),
    ),
    "NIAMS": Publisher(
        key="NIAMS",
        name="NIAMS (US National Institutes of Health)",
        license=US_GOV_PD,
        evidence_grade="patient_guideline",
        content_selector=".syndicate",
        drop_headings=("related resources", "view/download/order", "share this page"),
    ),
    "DAILYMED": Publisher(
        key="DAILYMED",
        name="DailyMed (US National Library of Medicine)",
        license=US_GOV_PD,
        evidence_grade="regulatory_label",
        content_selector="",
    ),
    "EUROPEPMC": Publisher(
        key="EUROPEPMC",
        name="Europe PMC (peer-reviewed, open access)",
        license=CC_BY,  # per-article licence overrides this
        evidence_grade="narrative_review",
        content_selector="",
    ),
}

# Keys allowed in evidence_documents.source. Anything else is rejected at ingest.
ALLOWED_SOURCES = frozenset(PUBLISHERS)


WEB_PAGES: list[WebPage] = [
    # --- NHS (verified 2026-09; several older URLs now 404 and were dropped) ---
    WebPage("NHS", "hair-loss", "https://www.nhs.uk/symptoms/hair-loss/"),
    WebPage("NHS", "dandruff", "https://www.nhs.uk/conditions/dandruff/"),
    WebPage("NHS", "ringworm", "https://www.nhs.uk/conditions/ringworm/"),
    WebPage("NHS", "psoriasis", "https://www.nhs.uk/conditions/psoriasis/", "both"),
    WebPage("NHS", "lichen-planus", "https://www.nhs.uk/conditions/lichen-planus/", "both"),
    WebPage("NHS", "iron-deficiency-anaemia", "https://www.nhs.uk/conditions/iron-deficiency-anaemia/"),
    WebPage("NHS", "underactive-thyroid", "https://www.nhs.uk/conditions/underactive-thyroid-hypothyroidism/"),
    WebPage("NHS", "pmos", "https://www.nhs.uk/conditions/polyendocrine-metabolic-ovarian-syndrome-pmos/"),
    # NHS medicine pages are hubs; the dosing sub-page is deliberately omitted.
    WebPage("NHS", "finasteride-about", "https://www.nhs.uk/medicines/finasteride/about-finasteride/"),
    WebPage(
        "NHS", "finasteride-who-can-take",
        "https://www.nhs.uk/medicines/finasteride/who-can-and-cannot-take-finasteride/",
    ),
    WebPage("NHS", "finasteride-side-effects", "https://www.nhs.uk/medicines/finasteride/side-effects-of-finasteride/"),
    WebPage(
        "NHS", "finasteride-pregnancy",
        "https://www.nhs.uk/medicines/finasteride/fertility-and-pregnancy-while-taking-finasteride/",
    ),
    WebPage(
        "NHS", "finasteride-common-questions",
        "https://www.nhs.uk/medicines/finasteride/common-questions-about-finasteride/",
    ),
    # Skin domain is implemented but not exposed; kept grounded all the same.
    WebPage("NHS", "acne", "https://www.nhs.uk/conditions/acne/", "skin"),
    WebPage("NHS", "sun-safety", "https://www.nhs.uk/live-well/seasonal-health/sunscreen-and-sun-safety/", "skin"),
    # --- MedlinePlus (NLM) ---
    WebPage("MEDLINEPLUS", "hair-loss", "https://medlineplus.gov/hairloss.html"),
    WebPage("MEDLINEPLUS", "hair-problems", "https://medlineplus.gov/hairproblems.html"),
    WebPage("MEDLINEPLUS", "androgenetic-alopecia", "https://medlineplus.gov/genetics/condition/androgenetic-alopecia/"),
    WebPage("MEDLINEPLUS", "alopecia-areata", "https://medlineplus.gov/genetics/condition/alopecia-areata/"),
    # --- NIAMS (NIH) ---
    WebPage("NIAMS", "alopecia-areata", "https://www.niams.nih.gov/health-topics/alopecia-areata"),
    WebPage(
        "NIAMS", "alopecia-areata-treatment",
        "https://www.niams.nih.gov/health-topics/alopecia-areata/diagnosis-treatment-and-steps-to-take",
    ),
]

@dataclass(frozen=True)
class LiteratureTopic:
    """A literature query scoped to article TITLES.

    Europe PMC searches full text by default, and the first corpus build proved
    why that is dangerous: sorting full-text matches by citation count surfaced
    famous reviews on SARS-CoV-2, breast cancer and industrial lipases that
    mention alopecia once in passing. An LLM handed those as "hair evidence"
    will cite them. So topics must appear in the title, and ``title_terms`` is
    re-checked on every fetched article as a second gate.
    """

    slug: str
    title_query: str
    title_terms: tuple[str, ...]


_HAIR = ("hair", "alopecia", "scalp", "follic", "baldness", "effluvium", "trich")

LITERATURE_TOPICS: list[LiteratureTopic] = [
    LiteratureTopic("hair-follicle-cycle",
                    'TITLE:("hair follicle" OR "hair cycle" OR "hair growth cycle")', ("hair",)),
    LiteratureTopic("androgenetic-alopecia",
                    'TITLE:("androgenetic alopecia" OR "androgenic alopecia" OR "male pattern baldness" '
                    'OR "male pattern hair loss")', ("alopecia", "pattern")),
    LiteratureTopic("female-pattern",
                    'TITLE:("female pattern hair loss" OR "female pattern alopecia")', ("female",)),
    LiteratureTopic("alopecia-areata", 'TITLE:("alopecia areata")', ("alopecia areata",)),
    LiteratureTopic("telogen-effluvium", 'TITLE:("telogen effluvium")', ("effluvium",)),
    LiteratureTopic("minoxidil", 'TITLE:(minoxidil)', ("minoxidil",)),
    LiteratureTopic("finasteride",
                    'TITLE:(finasteride OR dutasteride) AND TITLE:(alopecia OR hair)', ("finasteride", "dutasteride")),
    LiteratureTopic("seborrheic-dermatitis",
                    'TITLE:("seborrheic dermatitis" OR "seborrhoeic dermatitis" OR dandruff)',
                    ("seborrh", "dandruff")),
    LiteratureTopic("scarring-alopecia",
                    'TITLE:("lichen planopilaris" OR "frontal fibrosing alopecia" OR "cicatricial alopecia" '
                    'OR "scarring alopecia")', ("alopecia", "planopilaris")),
    LiteratureTopic("trichoscopy", 'TITLE:(trichoscopy OR "hair dermoscopy" OR "dermoscopy of hair")',
                    ("trichoscop", "dermoscop")),
    LiteratureTopic("traction-alopecia", 'TITLE:("traction alopecia")', ("traction",)),
    LiteratureTopic("nutrition-hair",
                    'TITLE:("hair loss" OR alopecia) AND TITLE:(iron OR ferritin OR "vitamin D" OR nutrition '
                    'OR micronutrient OR diet)', _HAIR),
    LiteratureTopic("tinea-capitis", 'TITLE:("tinea capitis")', ("tinea",)),
    LiteratureTopic("prp", 'TITLE:("platelet-rich plasma" OR "platelet rich plasma") AND TITLE:(alopecia OR hair)',
                    ("platelet",)),
    LiteratureTopic("hair-loss-diagnosis",
                    'TITLE:("hair loss" OR alopecia) AND TITLE:(diagnosis OR approach OR evaluation OR clinical)',
                    _HAIR),
]
