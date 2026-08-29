"""Seed medical evidence corpus for the MVP.

These are ORIGINAL, paraphrased summaries of publicly available guidance from
approved sources (AAD, FDA, NICE, NHS, peer-reviewed / systematic reviews). They
are intentionally short and non-verbatim to respect copyright. In production the
admin ingestion pipeline loads fuller curated content. Social media is never a source.

Each entry: source (must be in ALLOWED_SOURCES), title, url, publisher, grade,
domain, and `text` (the retrievable summary).
"""

from __future__ import annotations

SEED_DOCUMENTS: list[dict] = [
    {
        "source": "AAD",
        "title": "Hair loss: overview and when to see a dermatologist",
        "url": "https://www.aad.org/public/diseases/hair-loss",
        "publisher": "American Academy of Dermatology",
        "evidence_grade": "guideline",
        "domain": "hair",
        "text": (
            "Many causes of hair thinning are treatable, and outcomes are better when addressed early. "
            "Sudden, patchy, or scarring hair loss, or a painful/scaly scalp, should be evaluated by a "
            "dermatologist rather than self-treated. A clinician can distinguish patterned hair loss from "
            "other causes and discuss appropriate options."
        ),
    },
    {
        "source": "FDA",
        "title": "Topical minoxidil for hair regrowth (OTC)",
        "url": "https://www.fda.gov/drugs",
        "publisher": "U.S. Food and Drug Administration",
        "evidence_grade": "regulatory_label",
        "domain": "hair",
        "text": (
            "Over-the-counter topical minoxidil is approved to help regrow hair in some people with "
            "hereditary hair thinning. It must be used consistently; results, if any, typically take months, "
            "and benefit is lost if stopped. Users should follow label directions and stop if scalp irritation "
            "or unexpected symptoms occur."
        ),
    },
    {
        "source": "NICE",
        "title": "Androgenetic alopecia: management principles",
        "url": "https://cks.nice.org.uk/topics/",
        "publisher": "National Institute for Health and Care Excellence (CKS)",
        "evidence_grade": "guideline",
        "domain": "hair",
        "text": (
            "Patterned (androgenetic) hair loss is common and benign. Some medications used for it are "
            "prescription-only and require clinician assessment of suitability, benefits, and risks. Realistic "
            "expectations matter: treatments may slow progression or partially regrow hair but are not cures."
        ),
    },
    {
        "source": "NHS",
        "title": "Seborrhoeic dermatitis and dandruff self-care",
        "url": "https://www.nhs.uk/conditions/seborrhoeic-dermatitis/",
        "publisher": "NHS",
        "evidence_grade": "guideline",
        "domain": "hair",
        "text": (
            "Flaky, itchy scalp is often seborrhoeic dermatitis. Antifungal or medicated shampoos "
            "(e.g. containing ketoconazole or zinc pyrithione) used as directed can help control it. Persistent, "
            "severe, or spreading scalp inflammation should be reviewed by a clinician."
        ),
    },
    {
        "source": "systematic_review",
        "title": "Gentle hair and scalp care reduces mechanical damage",
        "url": "https://pubmed.ncbi.nlm.nih.gov/",
        "publisher": "Peer-reviewed dermatology literature",
        "evidence_grade": "systematic_review",
        "domain": "hair",
        "text": (
            "Reducing traction, excessive heat, and harsh chemical treatments limits mechanical and "
            "breakage-related hair damage. Gentle washing and avoiding tight hairstyles support hair and scalp "
            "health. These measures are supportive and do not treat underlying patterned hair loss."
        ),
    },
    {
        "source": "AAD",
        "title": "Alopecia areata: when to seek care",
        "url": "https://www.aad.org/public/diseases/hair-loss/types/alopecia-areata",
        "publisher": "American Academy of Dermatology",
        "evidence_grade": "guideline",
        "domain": "hair",
        "text": (
            "Alopecia areata typically causes sudden, round patches of hair loss and is an autoimmune "
            "condition. It should be assessed by a clinician, who can discuss management options. Self-treatment "
            "is not appropriate for undiagnosed patchy loss."
        ),
    },
    {
        "source": "AAD",
        "title": "Skin cancer warning signs (ABCDEs)",
        "url": "https://www.aad.org/public/diseases/skin-cancer",
        "publisher": "American Academy of Dermatology",
        "evidence_grade": "guideline",
        "domain": "skin",
        "text": (
            "Moles or spots that show Asymmetry, irregular Borders, multiple Colors, a large Diameter, or are "
            "Evolving warrant prompt evaluation by a dermatologist. Any new, changing, bleeding, or non-healing "
            "lesion should be checked in person. Imaging apps cannot diagnose skin cancer."
        ),
    },
    {
        "source": "NHS",
        "title": "Acne self-care and when to get medical advice",
        "url": "https://www.nhs.uk/conditions/acne/",
        "publisher": "NHS",
        "evidence_grade": "guideline",
        "domain": "skin",
        "text": (
            "Mild acne can often be managed with gentle cleansing and over-the-counter products; avoid harsh "
            "scrubbing and picking. Persistent, painful, cystic, or scarring acne should be assessed by a "
            "clinician, who can discuss prescription options if appropriate."
        ),
    },
    {
        "source": "AAD",
        "title": "Sunscreen use for skin protection",
        "url": "https://www.aad.org/public/everyday-care/sun-protection/sunscreen-patients",
        "publisher": "American Academy of Dermatology",
        "evidence_grade": "guideline",
        "domain": "skin",
        "text": (
            "Broad-spectrum sunscreen of at least SPF 30, applied daily and reapplied as directed, helps protect "
            "against UV damage, photoaging, and skin cancer. Sunscreen is a foundational step in most skin-care "
            "routines regardless of skin type."
        ),
    },
    {
        "source": "systematic_review",
        "title": "Moisturizers support skin barrier function",
        "url": "https://pubmed.ncbi.nlm.nih.gov/",
        "publisher": "Peer-reviewed dermatology literature",
        "evidence_grade": "systematic_review",
        "domain": "skin",
        "text": (
            "Regular use of moisturizers containing humectants and emollients improves skin hydration and "
            "supports barrier function, reducing dryness and irritation. Fragrance-free formulations are generally "
            "preferred for sensitive or reactive skin."
        ),
    },
    {
        "source": "NICE",
        "title": "Topical retinoids: use and cautions",
        "url": "https://bnf.nice.org.uk/",
        "publisher": "NICE / BNF",
        "evidence_grade": "guideline",
        "domain": "skin",
        "text": (
            "Topical retinoids can improve acne and skin texture but commonly cause initial dryness and "
            "irritation and increase sun sensitivity. Some retinoids are prescription-only. Introduce gradually, "
            "use sunscreen, and avoid combining multiple strong actives without guidance."
        ),
    },
    {
        "source": "systematic_review",
        "title": "Patch testing before new topical products",
        "url": "https://pubmed.ncbi.nlm.nih.gov/",
        "publisher": "Peer-reviewed dermatology literature",
        "evidence_grade": "expert_review",
        "domain": "both",
        "text": (
            "Introducing one new product at a time and patch-testing on a small area helps identify irritation "
            "or allergy before full-face or full-scalp use. Fragrances and certain preservatives are common "
            "irritants. Stop use and seek advice if a strong reaction occurs."
        ),
    },
]
