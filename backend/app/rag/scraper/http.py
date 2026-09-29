"""A polite async HTTP client for corpus collection.

Politeness is not optional here — these are public-service health websites:

* robots.txt is honoured for every host, APIs included. When a host disallows
  us (NCBI E-utilities does, for all agents), we use a different official
  route (Europe PMC) rather than ignore the rule.
* Requests to a host are spaced by a minimum interval.
* 429 and 5xx responses back off exponentially and honour Retry-After.
* Responses are cached on disk, so re-running the build does not re-fetch.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from pathlib import Path
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx

log = logging.getLogger("hairgpt.scraper")

USER_AGENT = "HairGPT-corpus-builder/1.0 (educational research project; respects robots.txt)"


class RobotsDisallowed(RuntimeError):
    """Raised when robots.txt forbids a URL. Callers must not work around it."""


class PoliteClient:
    def __init__(
        self,
        cache_dir: Path,
        min_interval: float = 1.0,
        per_host_interval: dict[str, float] | None = None,
        max_retries: int = 4,
        timeout: float = 30.0,
        use_cache: bool = True,
    ):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.min_interval = min_interval
        self.per_host_interval = per_host_interval or {}
        self.max_retries = max_retries
        self.use_cache = use_cache
        self._client = httpx.AsyncClient(
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
            timeout=timeout,
        )
        self._robots: dict[str, RobotFileParser] = {}
        self._last_hit: dict[str, float] = {}
        self._host_locks: dict[str, asyncio.Lock] = {}
        self.stats = {"fetched": 0, "cached": 0, "retries": 0}

    async def __aenter__(self) -> "PoliteClient":
        return self

    async def __aexit__(self, *exc) -> None:
        await self._client.aclose()

    # -- robots ----------------------------------------------------------------

    async def _robots_for(self, url: str) -> RobotFileParser:
        parts = urlparse(url)
        base = f"{parts.scheme}://{parts.netloc}"
        if base not in self._robots:
            parser = RobotFileParser()
            try:
                resp = await self._client.get(base + "/robots.txt")
                # A missing robots.txt means everything is allowed; any other
                # failure is treated as "allowed" per the robots convention.
                parser.parse(resp.text.splitlines() if resp.status_code == 200 else [])
            except httpx.HTTPError:
                parser.parse([])
            self._robots[base] = parser
        return self._robots[base]

    async def allowed(self, url: str) -> bool:
        return (await self._robots_for(url)).can_fetch(USER_AGENT, url)

    # -- rate limiting -----------------------------------------------------------

    async def _wait_turn(self, host: str) -> None:
        lock = self._host_locks.setdefault(host, asyncio.Lock())
        async with lock:
            interval = self.per_host_interval.get(host, self.min_interval)
            elapsed = time.monotonic() - self._last_hit.get(host, 0.0)
            if elapsed < interval:
                await asyncio.sleep(interval - elapsed)
            self._last_hit[host] = time.monotonic()

    # -- fetching ----------------------------------------------------------------

    def _cache_path(self, url: str) -> Path:
        digest = hashlib.sha256(url.encode()).hexdigest()[:24]
        return self.cache_dir / f"{digest}.json"

    async def get_text(self, url: str) -> tuple[str, str]:
        """Return (final_url, body_text). Raises RobotsDisallowed or httpx errors."""
        cache_file = self._cache_path(url)
        if self.use_cache and cache_file.exists():
            cached = json.loads(cache_file.read_text(encoding="utf-8"))
            self.stats["cached"] += 1
            return cached["final_url"], cached["body"]

        if not await self.allowed(url):
            raise RobotsDisallowed(url)

        host = urlparse(url).netloc
        delay = 2.0
        for attempt in range(self.max_retries + 1):
            await self._wait_turn(host)
            try:
                resp = await self._client.get(url)
            except httpx.TransportError as exc:
                if attempt == self.max_retries:
                    raise
                log.warning("transport error on %s (%s); retrying", url, exc)
                self.stats["retries"] += 1
                await asyncio.sleep(delay)
                delay *= 2
                continue

            if resp.status_code == 429 or resp.status_code >= 500:
                if attempt == self.max_retries:
                    resp.raise_for_status()
                retry_after = resp.headers.get("Retry-After")
                wait = float(retry_after) if retry_after and retry_after.isdigit() else delay
                log.warning("%s -> %s; backing off %.1fs", url, resp.status_code, wait)
                self.stats["retries"] += 1
                await asyncio.sleep(wait)
                delay *= 2
                continue

            resp.raise_for_status()
            body = resp.text
            final_url = str(resp.url)
            cache_file.write_text(
                json.dumps({"url": url, "final_url": final_url, "body": body}), encoding="utf-8"
            )
            self.stats["fetched"] += 1
            return final_url, body

        raise RuntimeError(f"unreachable: exhausted retries for {url}")

    async def get_json(self, url: str) -> dict:
        _, body = await self.get_text(url)
        return json.loads(body)
