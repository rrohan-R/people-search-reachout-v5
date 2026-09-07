import logging
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app import models, schemas
from app.deps import get_current_user
from app.routers.outreach import _call_out, _map_status
from app.services.hunar_client import HunarClient, HunarAPIError

logger = logging.getLogger("app.dashboard")

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

_TERMINAL_STATUSES = {
    models.CallStatusEnum.COMPLETED,
    models.CallStatusEnum.NOT_CONNECTED,
    models.CallStatusEnum.CANCELLED,
    models.CallStatusEnum.FAILED,
}


@router.get("/calls", response_model=List[schemas.CallOut])
def all_calls(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    q = (
        db.query(models.OutreachCall)
        .join(models.Candidate, models.OutreachCall.candidate_id == models.Candidate.id)
        .join(models.JobDescription, models.Candidate.job_description_id == models.JobDescription.id)
        .filter(models.JobDescription.owner_id == current_user.id)
    )
    if status:
        try:
            q = q.filter(models.OutreachCall.status == models.CallStatusEnum(status))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status '{status}'")
    calls = q.order_by(models.OutreachCall.created_at.desc()).all()
    return [_call_out(c) for c in calls]


@router.get("/calls/{call_id}", response_model=schemas.CallOut)
def call_detail(
    call_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    call = db.query(models.OutreachCall).filter(models.OutreachCall.id == call_id).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    if call.candidate.job_description.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your call")

    return _call_out(call)


@router.post("/calls/sync", response_model=List[schemas.CallOut])
def sync_calls(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Manually pull the latest status/result/recording for any non-terminal
    calls belonging to the current user. This is the only way call status
    gets updated (there is no inbound webhook receiver).
    """
    client = HunarClient()
    if not client.is_configured:
        raise HTTPException(status_code=400, detail="Calling is not configured yet.")

    calls = (
        db.query(models.OutreachCall)
        .join(models.Candidate, models.OutreachCall.candidate_id == models.Candidate.id)
        .join(models.JobDescription, models.Candidate.job_description_id == models.JobDescription.id)
        .filter(models.JobDescription.owner_id == current_user.id)
        .filter(models.OutreachCall.hunar_call_id.isnot(None))
        .all()
    )

    updated = []
    for call in calls:
        if call.status in _TERMINAL_STATUSES:
            continue
        try:
            data = client.get_call(call.hunar_call_id)
        except HunarAPIError:
            continue
        call.status = _map_status(data.get("status"))
        call.lifecycle_status = data.get("lifecycle_status")
        call.duration_seconds = data.get("duration_seconds")
        call.recording_url = data.get("recording_url") or call.recording_url
        call.result = data.get("result") or call.result
        call.answered_by = data.get("answered_by")
        call.engagement_status = data.get("engagement_status")
        updated.append(call)
    db.commit()
    for c in updated:
        db.refresh(c)
    return [_call_out(c) for c in updated]


@router.get("/summary")
def summary(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    jobs = db.query(models.JobDescription).filter(models.JobDescription.owner_id == current_user.id).all()
    job_ids = [j.id for j in jobs]
    candidate_count = db.query(models.Candidate).filter(models.Candidate.job_description_id.in_(job_ids)).count() if job_ids else 0
    calls = (
        db.query(models.OutreachCall)
        .join(models.Candidate, models.OutreachCall.candidate_id == models.Candidate.id)
        .filter(models.Candidate.job_description_id.in_(job_ids)).all()
        if job_ids else []
    )
    status_counts = {}
    for c in calls:
        key = c.status.value if hasattr(c.status, "value") else c.status
        status_counts[key] = status_counts.get(key, 0) + 1
    return {
        "job_count": len(jobs),
        "candidate_count": candidate_count,
        "call_count": len(calls),
        "status_counts": status_counts,
    }


@router.get("/jobs-overview", response_model=List[schemas.JobOverviewOut])
def jobs_overview(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Backs the grouped dashboard view: for each job description the user owns,
    return its title, how many candidates were found, and the list of calls
    placed so far (candidate name + call status), joining
    JobDescription -> Candidate -> OutreachCall.
    """
    jobs = (
        db.query(models.JobDescription)
        .filter(models.JobDescription.owner_id == current_user.id)
        .order_by(models.JobDescription.created_at.desc())
        .all()
    )

    overview: List[schemas.JobOverviewOut] = []
    for jd in jobs:
        candidate_count = db.query(func.count(models.Candidate.id)).filter(
            models.Candidate.job_description_id == jd.id
        ).scalar() or 0

        calls = (
            db.query(models.OutreachCall)
            .join(models.Candidate, models.OutreachCall.candidate_id == models.Candidate.id)
            .filter(models.Candidate.job_description_id == jd.id)
            .order_by(models.OutreachCall.created_at.desc())
            .all()
        )

        overview.append(
            schemas.JobOverviewOut(
                job_id=jd.id,
                title=jd.title,
                candidate_count=candidate_count,
                calls=[_call_out(c) for c in calls],
            )
        )

    return overview
