"""SEC EDGAR API client — respects fair-access rate limits (10 req/s max)."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

EDGAR_BASE = "https://data.sec.gov"
EFTS_BASE = "https://efts.sec.gov"
_client: httpx.AsyncClient | None = None
_semaphore = asyncio.Semaphore(5)   # max concurrent requests to SEC


def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            headers={"User-Agent": settings.sec_user_agent, "Accept-Encoding": "gzip,deflate"},
            timeout=httpx.Timeout(20.0),
            follow_redirects=True,
        )
    return _client


async def close_client() -> None:
    global _client
    if _client and not _client.is_closed:
        await _client.aclose()


async def _get(url: str, params: dict | None = None, retries: int = 3) -> Any:
    async with _semaphore:
        for attempt in range(retries):
            try:
                resp = await get_client().get(url, params=params)
                if resp.status_code == 429:
                    await asyncio.sleep(2 ** attempt)
                    continue
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code < 500 and exc.response.status_code != 429:
                    raise
                logger.warning("SEC EDGAR attempt %d: %s", attempt + 1, exc)
                await asyncio.sleep(1.5 ** attempt)
    raise RuntimeError(f"SEC EDGAR unavailable after {retries} attempts: {url}")


async def get_company_facts(cik: str) -> dict:
    """Full XBRL facts for a company — financials, filings, etc."""
    padded = str(cik).zfill(10)
    return await _get(f"{EDGAR_BASE}/api/xbrl/companyfacts/CIK{padded}.json")


async def get_company_concept(cik: str, taxonomy: str, concept: str) -> dict:
    padded = str(cik).zfill(10)
    return await _get(f"{EDGAR_BASE}/api/xbrl/companyconcept/CIK{padded}/{taxonomy}/{concept}.json")


async def search_filings(
    query: str,
    form_type: str | None = None,
    date_range: tuple[str, str] | None = None,
    size: int = 20,
) -> dict:
    """Full-text search across all SEC filings."""
    params: dict = {"q": f'"{query}"', "dateRange": "custom", "hits.hits.total.value": size}
    if form_type:
        params["forms"] = form_type
    if date_range:
        params["startdt"], params["enddt"] = date_range
    return await _get(f"{EFTS_BASE}/LATEST/search-index", params=params)


async def get_recent_form4(cik: str | None = None, limit: int = 40) -> list[dict]:
    """Fetch recent Form 4 (insider transactions) from EDGAR submissions."""
    if cik:
        padded = str(cik).zfill(10)
        data = await _get(f"{EDGAR_BASE}/submissions/CIK{padded}.json")
        recent = data.get("filings", {}).get("recent", {})
        indices = [
            i for i, f in enumerate(recent.get("form", []))
            if f in ("4", "4/A")
        ][:limit]
        return [
            {
                "accession": recent["accessionNumber"][i].replace("-", ""),
                "filed": recent["filingDate"][i],
                "form": recent["form"][i],
                "cik": cik,
            }
            for i in indices
        ]
    # Broad recent Form 4 via EDGAR full-text search
    result = await search_filings("insider transaction", form_type="4", size=limit)
    hits = result.get("hits", {}).get("hits", [])
    return [h.get("_source", {}) for h in hits]


async def get_13f_holdings(cik: str) -> list[dict]:
    """Parse 13F-HR institutional holdings for a given fund CIK."""
    padded = str(cik).zfill(10)
    data = await _get(f"{EDGAR_BASE}/submissions/CIK{padded}.json")
    recent = data.get("filings", {}).get("recent", {})
    holdings = []
    for i, form in enumerate(recent.get("form", [])):
        if form == "13F-HR":
            holdings.append({
                "accession": recent["accessionNumber"][i],
                "filed": recent["filingDate"][i],
                "primary_doc": recent.get("primaryDocument", [""])[i],
            })
    return holdings[:10]
