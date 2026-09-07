import logging
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.deps import get_current_user
from app.services.hunar_client import HunarClient, HunarAPIError
from app.services.scheduling import validate_guardrails, normalize_allowed_days, is_within_window
from app.routers.outreach import _build_custom_data, _map_status

logger = logging.getLogger("app.schedules")

router = APIRouter(prefix="/api/schedules", tags=["schedules"])


def _get_owned_schedule(db: Session, schedule_id: str, current_user: models.User) -> models.CallSchedule:
    schedule = db.query(models.CallSchedule).filter(models.CallSchedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    if schedule.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your schedule")
    return schedule


def _schedule_out(schedule: models.CallSchedule) -> schemas.CallScheduleOut:
    candidate = schedule.candidate
    call = schedule.outreach_call
    return schemas.CallScheduleOut(
        id=schedule.id,
        candidate_id=schedule.candidate_id,
        candidate_name=candidate.full_name if candidate else None,
        candidate_title=candidate.title if candidate else None,
        candidate_company=candidate.company if candidate else None,
        candidate_phone=candidate.phone_number if candidate else None,
        job_description_id=candidate.job_description_id if candidate else None,
        job_description_title=candidate.job_description.title if candidate and candidate.job_description else None,
        agent_id=schedule.agent_id,
        agent_name=schedule.agent.name if schedule.agent else None,
        allowed_days=schedule.allowed_days or [],
        earliest_call_time=schedule.earliest_call_time,
        last_call_time=schedule.last_call_time,
        timezone=schedule.timezone,
        notes=schedule.notes,
        extra_custom_data=schedule.extra_custom_data or {},
        status=schedule.status.value if hasattr(schedule.status, "value") else schedule.status,
        failure_reason=schedule.failure_reason,
        outreach_call_id=schedule.outreach_call_id,
        outreach_call_status=(call.status.value if call and hasattr(call.status, "value") else (call.status if call else None)),
        created_at=schedule.created_at,
        updated_at=schedule.updated_at,
    )


def _get_owned_candidate(db: Session, candidate_id: str, current_user: models.User) -> models.Candidate:
    candidate = db.query(models.Candidate).filter(models.Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    if not candidate.job_description or candidate.job_description.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your candidate")
    return candidate


def _get_owned_agent(db: Session, agent_id: str, current_user: models.User) -> models.Agent:
    agent = db.query(models.Agent).filter(models.Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if agent.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your agent")
    return agent


@router.post("", response_model=schemas.CallScheduleOut, status_code=201)
def create_schedule(
    payload: schemas.CallScheduleCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    candidate = _get_owned_candidate(db, payload.candidate_id, current_user)
    if not candidate.phone_number:
        raise HTTPException(
            status_code=400,
            detail=f"Add a phone number for {candidate.full_name} before scheduling a call.",
        )
    agent = _get_owned_agent(db, payload.agent_id, current_user)
    if not agent.is_active:
        raise HTTPException(status_code=400, detail="This agent is inactive; activate it or pick another.")

    try:
        validate_guardrails(payload.allowed_days, payload.earliest_call_time, payload.last_call_time, payload.timezone)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    schedule = models.CallSchedule(
        owner_id=current_user.id,
        candidate_id=candidate.id,
        agent_id=agent.id,
        allowed_days=normalize_allowed_days(payload.allowed_days),
        earliest_call_time=payload.earliest_call_time,
        last_call_time=payload.last_call_time,
        timezone=payload.timezone,
        notes=payload.notes,
        extra_custom_data=payload.extra_custom_data or {},
        status=models.ScheduleStatusEnum.PENDING,
    )
    db.add(schedule)
    db.commit()
    db.refresh(schedule)

    # If the window is open right now, no need to make the user wait for the
    # background dispatcher's next tick -- send it immediately.
    if is_within_window(schedule.allowed_days, schedule.earliest_call_time, schedule.last_call_time, schedule.timezone):
        _dispatch_schedule(db, schedule)
        db.refresh(schedule)

    return _schedule_out(schedule)


@router.get("", response_model=List[schemas.CallScheduleOut])
def list_schedules(
    status: Optional[str] = None,
    job_id: Optional[str] = None,
    candidate_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    q = db.query(models.CallSchedule).filter(models.CallSchedule.owner_id == current_user.id)
    if status:
        try:
            q = q.filter(models.CallSchedule.status == models.ScheduleStatusEnum(status))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status '{status}'")
    if candidate_id:
        q = q.filter(models.CallSchedule.candidate_id == candidate_id)
    if job_id:
        q = q.join(models.Candidate, models.CallSchedule.candidate_id == models.Candidate.id).filter(
            models.Candidate.job_description_id == job_id
        )
    schedules = q.order_by(models.CallSchedule.created_at.desc()).all()
    return [_schedule_out(s) for s in schedules]


@router.get("/{schedule_id}", response_model=schemas.CallScheduleOut)
def get_schedule(
    schedule_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return _schedule_out(_get_owned_schedule(db, schedule_id, current_user))


@router.put("/{schedule_id}", response_model=schemas.CallScheduleOut)
def update_schedule(
    schedule_id: str,
    payload: schemas.CallScheduleUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    schedule = _get_owned_schedule(db, schedule_id, current_user)
    if schedule.status != models.ScheduleStatusEnum.PENDING:
        raise HTTPException(
            status_code=400,
            detail="Only pending schedules can be edited. This one has already been "
                   "dispatched, cancelled, or failed -- delete it and create a new one instead.",
        )

    if payload.agent_id is not None:
        agent = _get_owned_agent(db, payload.agent_id, current_user)
        schedule.agent_id = agent.id

    new_days = payload.allowed_days if payload.allowed_days is not None else schedule.allowed_days
    new_earliest = payload.earliest_call_time or schedule.earliest_call_time
    new_last = payload.last_call_time or schedule.last_call_time
    new_tz = payload.timezone or schedule.timezone
    try:
        validate_guardrails(new_days, new_earliest, new_last, new_tz)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    schedule.allowed_days = normalize_allowed_days(new_days)
    schedule.earliest_call_time = new_earliest
    schedule.last_call_time = new_last
    schedule.timezone = new_tz
    if payload.notes is not None:
        schedule.notes = payload.notes
    if payload.extra_custom_data is not None:
        schedule.extra_custom_data = payload.extra_custom_data

    db.commit()
    db.refresh(schedule)

    if is_within_window(schedule.allowed_days, schedule.earliest_call_time, schedule.last_call_time, schedule.timezone):
        _dispatch_schedule(db, schedule)
        db.refresh(schedule)

    return _schedule_out(schedule)


@router.delete("/{schedule_id}", status_code=204)
def delete_schedule(
    schedule_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Deletes the schedule row. If it's still PENDING this is a real,
    guaranteed cancellation -- since this app is the only thing that ever
    dispatches a pending schedule, removing it here means it will never be
    sent to Hunar. If it was already DISPATCHED, the underlying call (visible
    on the Conversations page) is untouched; use "Cancel call" there instead.
    """
    schedule = _get_owned_schedule(db, schedule_id, current_user)
    db.delete(schedule)
    db.commit()
    return None


@router.post("/{schedule_id}/call-now", response_model=schemas.CallScheduleOut)
def dispatch_schedule_now(
    schedule_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Skip waiting for the window and dispatch a PENDING schedule immediately."""
    schedule = _get_owned_schedule(db, schedule_id, current_user)
    if schedule.status != models.ScheduleStatusEnum.PENDING:
        raise HTTPException(status_code=400, detail="This schedule isn't pending anymore.")
    _dispatch_schedule(db, schedule)
    db.refresh(schedule)
    return _schedule_out(schedule)


def _dispatch_schedule(db: Session, schedule: models.CallSchedule) -> None:
    """
    Turn a PENDING schedule into a real Hunar call, forwarding its window as
    `guardrails` + `timezone` so Hunar paces the actual dial time. Shared by
    the manual "Call now" endpoint above and the background loop in main.py.
    """
    candidate = schedule.candidate
    agent = schedule.agent
    jd = candidate.job_description if candidate else None

    if not candidate or not candidate.phone_number:
        schedule.status = models.ScheduleStatusEnum.FAILED
        schedule.failure_reason = "Candidate no longer has a phone number on file."
        db.commit()
        return
    if not agent:
        schedule.status = models.ScheduleStatusEnum.FAILED
        schedule.failure_reason = "The agent for this schedule was deleted."
        db.commit()
        return

    request_id = f"sched-{schedule.id[:8]}-{uuid.uuid4().hex[:6]}"
    custom_data = _build_custom_data(agent, jd, candidate, schedule.extra_custom_data)
    guardrails = {
        "allowed_days": schedule.allowed_days,
        "earliest_call_time": schedule.earliest_call_time,
        "last_call_time": schedule.last_call_time,
    }

    call_row = models.OutreachCall(
        candidate_id=candidate.id,
        mobile_number=candidate.phone_number,
        hunar_agent_id=agent.hunar_agent_id,
        request_id=request_id,
        status=models.CallStatusEnum.NOT_STARTED,
        triggered_by=schedule.owner.username if schedule.owner else None,
        guardrails=guardrails,
        timezone=schedule.timezone,
    )

    client = HunarClient()
    if client.is_configured:
        logger.info(
            "Dispatching scheduled call: schedule=%s candidate=%s agent=%s window=%s tz=%s",
            schedule.id, candidate.id, agent.hunar_agent_id, guardrails, schedule.timezone,
        )
        try:
            resp = client.create_call(
                agent_id=agent.hunar_agent_id,
                callee_name=candidate.full_name,
                mobile_number=candidate.phone_number,
                custom_data=custom_data,
                request_id=request_id,
                guardrails=guardrails,
                timezone=schedule.timezone,
            )
            call_row.hunar_call_id = resp.get("id")
            call_row.status = _map_status(resp.get("status"))
        except HunarAPIError as exc:
            call_row.status = models.CallStatusEnum.FAILED
            call_row.result = {"error": exc.message, "details": exc.details}
            schedule.status = models.ScheduleStatusEnum.FAILED
            schedule.failure_reason = exc.message
            db.add(call_row)
            db.commit()
            return
    else:
        call_row.result = {"info": "Calling is not yet configured for this account."}

    db.add(call_row)
    db.flush()
    schedule.status = models.ScheduleStatusEnum.DISPATCHED
    schedule.outreach_call_id = call_row.id
    db.commit()


def dispatch_due_schedules(db: Session) -> int:
    """
    Called every tick by the background loop in main.py. Finds PENDING
    schedules whose window is open right now (in their own timezone) and
    sends them. Returns how many were dispatched.
    """
    pending = db.query(models.CallSchedule).filter(
        models.CallSchedule.status == models.ScheduleStatusEnum.PENDING
    ).all()
    count = 0
    for schedule in pending:
        if is_within_window(schedule.allowed_days, schedule.earliest_call_time, schedule.last_call_time, schedule.timezone):
            _dispatch_schedule(db, schedule)
            count += 1
    return count
