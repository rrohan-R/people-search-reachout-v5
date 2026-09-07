import math
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.deps import get_current_user
from app.providers.factory import get_provider, list_providers
from app.routers.jobs import _get_owned_job

router = APIRouter(prefix="/api/jobs/{job_id}", tags=["search"])


@router.get("/providers")
def get_providers(current_user: models.User = Depends(get_current_user)):
    return list_providers()


@router.post("/search", response_model=schemas.PaginatedCandidates)
def search_candidates(
    job_id: str,
    payload: schemas.SearchRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    jd = _get_owned_job(db, job_id, current_user)

    keywords = payload.keywords if payload.keywords is not None else (jd.keywords or [])
    locations = payload.locations if payload.locations is not None else (jd.locations or [])
    seniority = payload.seniority if payload.seniority is not None else jd.seniority

    try:
        provider = get_provider(payload.provider)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    raw_results = provider.search(keywords, locations, seniority, limit=payload.limit)

    saved: List[models.Candidate] = []
    for r in raw_results:
        candidate = models.Candidate(
            job_description_id=jd.id,
            source_provider=provider.name if provider.name in [e.value for e in models.ProviderEnum] else models.ProviderEnum.MOCK,
            external_id=r.get("external_id"),
            full_name=r.get("full_name") or "Unknown",
            title=r.get("title"),
            company=r.get("company"),
            location=r.get("location"),
            linkedin_url=r.get("linkedin_url"),
            email=r.get("email"),
            phone_number=r.get("phone_number"),
            skills=r.get("skills") or [],
            raw_profile=r.get("raw_profile") or {},
        )
        db.add(candidate)
        saved.append(candidate)
    db.commit()
    for c in saved:
        db.refresh(c)

    items = [_candidate_out(c) for c in saved]
    return schemas.PaginatedCandidates(
        items=items,
        total=len(items),
        page=1,
        page_size=payload.limit,
        total_pages=1,
    )


@router.get("/candidates", response_model=schemas.PaginatedCandidates)
def list_candidates(
    job_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    jd = _get_owned_job(db, job_id, current_user)

    base_query = db.query(models.Candidate).filter(models.Candidate.job_description_id == jd.id)
    total = base_query.count()

    candidates = (
        base_query.order_by(models.Candidate.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    total_pages = math.ceil(total / page_size) if total else 0
    return schemas.PaginatedCandidates(
        items=[_candidate_out(c) for c in candidates],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/candidates/{candidate_id}", response_model=schemas.CandidateOut)
def get_candidate(
    job_id: str,
    candidate_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    jd = _get_owned_job(db, job_id, current_user)
    candidate = db.query(models.Candidate).filter(
        models.Candidate.id == candidate_id, models.Candidate.job_description_id == jd.id
    ).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return _candidate_out(candidate)


@router.patch("/candidates/{candidate_id}/phone", response_model=schemas.CandidateOut)
def update_candidate_phone(
    job_id: str,
    candidate_id: str,
    payload: schemas.CandidatePhoneUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    jd = _get_owned_job(db, job_id, current_user)
    candidate = db.query(models.Candidate).filter(
        models.Candidate.id == candidate_id, models.Candidate.job_description_id == jd.id
    ).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    candidate.phone_number = payload.phone_number
    db.commit()
    db.refresh(candidate)
    return _candidate_out(candidate)


def _candidate_out(c: models.Candidate) -> schemas.CandidateOut:
    latest_status = None
    latest_call_id = None
    if c.calls:
        latest = sorted(c.calls, key=lambda call: call.created_at, reverse=True)[0]
        latest_status = latest.status.value if hasattr(latest.status, "value") else latest.status
        latest_call_id = latest.id
    return schemas.CandidateOut(
        id=c.id,
        job_description_id=c.job_description_id,
        source_provider=c.source_provider.value if hasattr(c.source_provider, "value") else c.source_provider,
        external_id=c.external_id,
        full_name=c.full_name,
        title=c.title,
        company=c.company,
        location=c.location,
        linkedin_url=c.linkedin_url,
        email=c.email,
        phone_number=c.phone_number,
        skills=c.skills or [],
        created_at=c.created_at,
        latest_call_status=latest_status,
        latest_call_id=latest_call_id,
    )
