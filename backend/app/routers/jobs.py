from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app import models, schemas
from app.deps import get_current_user
from app.services.jd_parser import parse_job_description

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


def _to_out(jd: models.JobDescription, candidate_count: int = 0) -> schemas.JobDescriptionOut:
    return schemas.JobDescriptionOut(
        id=jd.id,
        title=jd.title,
        raw_text=jd.raw_text,
        keywords=jd.keywords or [],
        locations=jd.locations or [],
        seniority=jd.seniority,
        company_hint=jd.company_hint,
        created_at=jd.created_at,
        candidate_count=candidate_count,
    )


@router.post("", response_model=schemas.JobDescriptionOut, status_code=201)
def create_job(
    payload: schemas.JobDescriptionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    keywords, locations, seniority, company_hint = parse_job_description(payload.title, payload.raw_text)
    jd = models.JobDescription(
        title=payload.title,
        raw_text=payload.raw_text,
        keywords=payload.keywords if payload.keywords is not None else keywords,
        locations=payload.locations if payload.locations is not None else locations,
        seniority=payload.seniority if payload.seniority is not None else seniority,
        company_hint=payload.company_hint if payload.company_hint is not None else company_hint,
        owner_id=current_user.id,
    )
    db.add(jd)
    db.commit()
    db.refresh(jd)
    return _to_out(jd, 0)


@router.get("", response_model=List[schemas.JobDescriptionOut])
def list_jobs(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    rows = (
        db.query(models.JobDescription, func.count(models.Candidate.id))
        .outerjoin(models.Candidate, models.Candidate.job_description_id == models.JobDescription.id)
        .filter(models.JobDescription.owner_id == current_user.id)
        .group_by(models.JobDescription.id)
        .order_by(models.JobDescription.created_at.desc())
        .all()
    )
    return [_to_out(jd, count) for jd, count in rows]


@router.get("/{job_id}", response_model=schemas.JobDescriptionOut)
def get_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    jd = _get_owned_job(db, job_id, current_user)
    count = db.query(func.count(models.Candidate.id)).filter(
        models.Candidate.job_description_id == jd.id
    ).scalar()
    return _to_out(jd, count or 0)


@router.patch("/{job_id}/criteria", response_model=schemas.JobDescriptionOut)
def update_criteria(
    job_id: str,
    payload: schemas.JobDescriptionUpdateCriteria,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    jd = _get_owned_job(db, job_id, current_user)
    if payload.keywords is not None:
        jd.keywords = payload.keywords
    if payload.locations is not None:
        jd.locations = payload.locations
    if payload.seniority is not None:
        jd.seniority = payload.seniority
    if payload.company_hint is not None:
        jd.company_hint = payload.company_hint
    db.commit()
    db.refresh(jd)
    count = db.query(func.count(models.Candidate.id)).filter(
        models.Candidate.job_description_id == jd.id
    ).scalar()
    return _to_out(jd, count or 0)


@router.delete("/{job_id}", status_code=204)
def delete_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    jd = _get_owned_job(db, job_id, current_user)
    db.delete(jd)
    db.commit()
    return None


def _get_owned_job(db: Session, job_id: str, current_user: models.User) -> models.JobDescription:
    jd = db.query(models.JobDescription).filter(models.JobDescription.id == job_id).first()
    if not jd:
        raise HTTPException(status_code=404, detail="Job description not found")
    if jd.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your job description")
    return jd
