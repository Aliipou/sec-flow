from __future__ import annotations

from datetime import date, timedelta
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

from app.scrapers.edgar import get_recent_form4, get_company_facts, search_filings
from app.analysis.scoring import InsiderTransaction, FlowSummary

router = APIRouter(prefix="/flow", tags=["flow"])


class FilingOut(BaseModel):
    accession: str
    filed: str
    form: str
    cik: str | int | None = None


class CompanyConceptOut(BaseModel):
    cik: str
    entity_name: str
    label: str
    description: str
    unit: str
    data_points: int
    latest_value: float | None
    latest_filed: str | None


@router.get("/form4/recent", response_model=list[FilingOut])
async def recent_form4(
    cik: str | None = Query(default=None, description="Filter by company CIK"),
    limit: int = Query(default=20, ge=1, le=100),
) -> list[FilingOut]:
    """Recent Form 4 insider transactions — open to all."""
    try:
        filings = await get_recent_form4(cik, limit=limit)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"SEC EDGAR error: {exc}")
    return [FilingOut(**f) for f in filings if "accession" in f]


@router.get("/company/{cik}/concept/{taxonomy}/{concept}", response_model=CompanyConceptOut)
async def company_concept(cik: str, taxonomy: str, concept: str) -> CompanyConceptOut:
    """XBRL financial concept for a company — e.g. us-gaap/NetIncomeLoss."""
    try:
        data = await get_company_facts(cik)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    units = data.get("facts", {}).get(taxonomy, {}).get(concept, {})
    if not units:
        raise HTTPException(status_code=404, detail=f"Concept {taxonomy}/{concept} not found for CIK {cik}")

    all_entries = []
    for unit_data in units.get("units", {}).values():
        all_entries.extend(unit_data)

    all_entries.sort(key=lambda x: x.get("filed", ""), reverse=True)
    latest = all_entries[0] if all_entries else {}

    return CompanyConceptOut(
        cik=cik,
        entity_name=data.get("entityName", ""),
        label=units.get("label", concept),
        description=units.get("description", "")[:300],
        unit=next(iter(units.get("units", {}).keys()), ""),
        data_points=len(all_entries),
        latest_value=latest.get("val"),
        latest_filed=latest.get("filed"),
    )


@router.get("/search")
async def search(
    q: str = Query(min_length=2, max_length=200),
    form: str | None = Query(default=None, description="Form type, e.g. '4', '13F-HR'"),
    since: str | None = Query(default=None, description="YYYY-MM-DD"),
    until: str | None = Query(default=None, description="YYYY-MM-DD"),
    size: int = Query(default=20, ge=1, le=100),
) -> dict:
    """Full-text search across all SEC EDGAR filings."""
    date_range = (since, until) if since and until else None
    try:
        results = await search_filings(q, form_type=form, date_range=date_range, size=size)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    hits = results.get("hits", {}).get("hits", [])
    return {
        "total": results.get("hits", {}).get("total", {}).get("value", 0),
        "results": [
            {
                "accession": h.get("_id"),
                "entity_name": h.get("_source", {}).get("entity_name"),
                "form": h.get("_source", {}).get("file_type"),
                "filed": h.get("_source", {}).get("file_date"),
                "description": h.get("_source", {}).get("period_of_report"),
            }
            for h in hits
        ],
    }
