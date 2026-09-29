"""Build the HairGPT evidence corpus.

    python -m app.rag.scraper.run                    # everything, using the cache
    python -m app.rag.scraper.run --pmc-per-topic 4  # more literature per topic
    python -m app.rag.scraper.run --refresh          # ignore the on-disk cache

Output:
    data/corpus/documents.jsonl   one document per line, sorted by doc_id
    data/corpus/SOURCES.md        attribution for every document (required by
                                  the Open Government Licence and CC BY)
    data/corpus/raw/              HTTP cache (git-ignored)
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from app.rag.sanitize import drop_injection_sentences
from app.rag.scraper import dailymed, europepmc
from app.rag.scraper.html_extract import Section, extract
from app.rag.scraper.http import PoliteClient, RobotsDisallowed
from app.rag.sources import (
    EUROPEPMC_ALLOWED_LICENSES,
    LITERATURE_TOPICS,
    PUBLISHERS,
    WEB_PAGES,
)

log = logging.getLogger("hairgpt.scraper")

BACKEND_ROOT = Path(__file__).resolve().parents[3]
CORPUS_DIR = BACKEND_ROOT / "data" / "corpus"
CORPUS_FILE = CORPUS_DIR / "documents.jsonl"

# Politeness intervals per host (seconds between requests).
HOST_INTERVALS = {
    "www.nhs.uk": 1.5,
    "medlineplus.gov": 1.0,
    "www.niams.nih.gov": 1.0,
    "dailymed.nlm.nih.gov": 1.0,
    "www.ebi.ac.uk": 0.5,
}


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _clean(sections: list[Section], stats: Counter) -> list[dict]:
    out = []
    for section in sections:
        text, removed = drop_injection_sentences(section.text)
        stats["injection_sentences_removed"] += removed
        if len(text.split()) >= 5:
            out.append({"heading": section.heading, "text": text})
    return out


def _hash(sections: list[dict]) -> str:
    body = "\n".join(f"{s['heading']}\n{s['text']}" for s in sections)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


async def collect_web(client: PoliteClient, stats: Counter) -> list[dict]:
    docs = []
    for page in WEB_PAGES:
        publisher = PUBLISHERS[page.source]
        try:
            final_url, html = await client.get_text(page.url)
        except RobotsDisallowed:
            log.warning("robots.txt disallows %s; skipped", page.url)
            stats["robots_skipped"] += 1
            continue
        except Exception as exc:
            log.warning("failed %s: %s", page.url, exc)
            stats["failed"] += 1
            continue
        extracted = extract(html, publisher)
        sections = _clean(extracted.sections, stats)
        if not sections:
            log.warning("no content extracted from %s", page.url)
            stats["empty"] += 1
            continue
        docs.append({
            "doc_id": f"{page.source}:{page.slug}",
            "source": page.source,
            "publisher": publisher.name,
            "title": extracted.title or page.slug.replace("-", " ").title(),
            "url": final_url,
            "domain": page.domain,
            "evidence_grade": publisher.evidence_grade,
            "source_type": "scraped",
            "license": publisher.license.spdx,
            "license_url": publisher.license.url,
            "attribution": f"{publisher.name}. {publisher.license.attribution}",
            "pub_date": extracted.last_reviewed.isoformat() if extracted.last_reviewed else None,
            "retrieved_at": _now(),
            "content_hash": _hash(sections),
            "sections": sections,
            "meta": {},
        })
    return docs


async def collect_literature(client: PoliteClient, per_topic: int, stats: Counter) -> list[dict]:
    docs: dict[str, dict] = {}
    for topic in LITERATURE_TOPICS:
        try:
            hits = await europepmc.search(client, topic, per_topic)
        except Exception as exc:
            log.warning("Europe PMC search failed for %s: %s", topic.slug, exc)
            stats["failed"] += 1
            continue
        stats[f"topic:{topic.slug}"] = len(hits)
        for meta in hits:
            if meta["pmcid"] in docs:
                continue  # the same review often answers several topics
            article = await europepmc.fetch_article(client, meta)
            if article is None:
                stats["empty"] += 1
                continue
            if not europepmc.on_topic(article.title, topic):
                stats["off_topic_rejected"] += 1
                continue
            sections = _clean(article.sections, stats)
            if not sections:
                continue
            lic = EUROPEPMC_ALLOWED_LICENSES[article.license_key]
            citation = f"{article.authors} ({article.year}). {article.title}. {article.journal}."
            if article.doi:
                citation += f" doi:{article.doi}."
            docs[article.pmcid] = {
                "doc_id": f"EUROPEPMC:{article.pmcid}",
                "source": "EUROPEPMC",
                "publisher": article.journal or "Peer-reviewed journal",
                "title": article.title,
                "url": article.url,
                "domain": "hair",
                "evidence_grade": article.evidence_grade,
                "source_type": "scraped",
                "license": lic.spdx if article.license_key != "cc0" else "CC0-1.0",
                "license_url": lic.url,
                "attribution": f"{citation} Licensed under {article.license_key.upper()}.",
                "pub_date": f"{article.year}-01-01" if article.year else None,
                "retrieved_at": _now(),
                "content_hash": _hash(sections),
                "sections": sections,
                "meta": {
                    "pmcid": article.pmcid,
                    "doi": article.doi,
                    "journal": article.journal,
                    "authors": article.authors,
                    "pub_types": article.pub_types,
                    "topic": topic.slug,
                },
            }
    return list(docs.values())


async def collect_labels(client: PoliteClient, stats: Counter) -> list[dict]:
    publisher = PUBLISHERS["DAILYMED"]
    docs = []
    for label in await dailymed.fetch_labels(client):
        sections = _clean(label.sections, stats)
        if not sections:
            continue
        docs.append({
            "doc_id": f"DAILYMED:{label.setid}",
            "source": "DAILYMED",
            "publisher": publisher.name,
            "title": dailymed.PINNED_LABELS.get(label.setid, label.title),
            "url": label.url,
            "domain": "hair",
            "evidence_grade": publisher.evidence_grade,
            "source_type": "scraped",
            "license": publisher.license.spdx,
            "license_url": publisher.license.url,
            "attribution": f"{publisher.name}, label set {label.setid}. {publisher.license.attribution}",
            "pub_date": None,
            "retrieved_at": _now(),
            "content_hash": _hash(sections),
            "sections": sections,
            "meta": {"setid": label.setid, "spl_title": label.title},
        })
    return docs


def write_sources_md(docs: list[dict], path: Path) -> None:
    lines = [
        "# Evidence corpus — sources and attribution",
        "",
        "Generated by `python -m app.rag.scraper.run`. Every document below was",
        "collected from an openly-licensed publisher, honouring robots.txt, and is",
        "redistributed under the licence shown.",
        "",
        "Contains public sector information licensed under the Open Government Licence v3.0.",
        "",
        "| Document | Publisher | Licence | Link |",
        "|---|---|---|---|",
    ]
    for d in docs:
        title = d["title"].replace("|", "/")
        lines.append(f"| {title} | {d['publisher'].replace('|', '/')} | {d['license']} | [source]({d['url']}) |")
    lines += ["", "## Full attributions", ""]
    lines += [f"- **{d['doc_id']}** — {d['attribution']}" for d in docs]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


async def build(per_topic: int, refresh: bool) -> list[dict]:
    stats: Counter = Counter()
    async with PoliteClient(
        CORPUS_DIR / "raw", per_host_interval=HOST_INTERVALS, use_cache=not refresh
    ) as client:
        web = await collect_web(client, stats)
        labels = await collect_labels(client, stats)
        literature = await collect_literature(client, per_topic, stats)
        http_stats = dict(client.stats)

    docs = sorted(web + labels + literature, key=lambda d: d["doc_id"])
    CORPUS_DIR.mkdir(parents=True, exist_ok=True)
    with CORPUS_FILE.open("w", encoding="utf-8") as fh:
        for d in docs:
            fh.write(json.dumps(d, ensure_ascii=False) + "\n")
    write_sources_md(docs, CORPUS_DIR / "SOURCES.md")

    by_source = Counter(d["source"] for d in docs)
    words = sum(len(s["text"].split()) for d in docs for s in d["sections"])
    print(f"documents: {len(docs)}  words: {words:,}  by source: {dict(by_source)}")
    print(f"http: {http_stats}  issues: {dict(stats)}")
    print(f"wrote {CORPUS_FILE.relative_to(BACKEND_ROOT)}")
    return docs


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pmc-per-topic", type=int, default=3)
    parser.add_argument("--refresh", action="store_true", help="ignore the HTTP cache")
    args = parser.parse_args()
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    asyncio.run(build(args.pmc_per_topic, args.refresh))


if __name__ == "__main__":
    main()
