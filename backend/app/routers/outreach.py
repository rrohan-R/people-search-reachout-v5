import logging
import uuid
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.deps import get_current_user
from app.routers.jobs import _get_owned_job
from app.services.hunar_client import HunarClient, HunarAPIError

logger = logging.getLogger("app.outreach")

router = APIRouter(prefix="/api/jobs/{job_id}", tags=["outreach"])


def _build_custom_data(
    agent: models.Agent,
    jd: models.JobDescription,
    candidate: models.Candidate,
    extra_custom_data: Dict[str, Any] | None,
) -> Dict[str, Any]:
    """
    Build the `custom_data` payload for a call.

    Hunar rejects a call with a 422 ("Custom data keys are not present: {...}")
    if `custom_data` is missing any variable the agent's prompt/introduction
    actually references (`agent.custom_variables`, echoed back by Hunar when
    the agent was created). Previously this hardcoded exactly three keys
    (job_role/company/location) regardless of what the agent needed — any
    agent using a different variable name, or an extra one, would silently
    fail every call. Instead, fill every variable Hunar told us the agent
    needs, falling back to known job/candidate fields, then "" if we have no
    mapping for it (still satisfies the "key must be present" requirement).
    """
    known: Dict[str, Any] = {
        "job_role": jd.title,
        "company": agent.company or candidate.company or jd.company_hint or "",
        "location": candidate.location or "",
        "candidate_name": candidate.full_name,
        "candidate_title": candidate.title or "",
    }
    extra = extra_custom_data or {}

    required_vars = agent.custom_variables or []
    custom_data: Dict[str, Any] = {}
    for var in required_vars:
        if var in extra:
            custom_data[var] = extra[var]
        elif var in known:
            custom_data[var] = known[var]
        else:
            logger.warning(
                "Agent %s expects custom variable '%s' but no value is available for "
                "candidate %s — sending an empty string. Add it to the agent's "
                "prompt/introduction differently, or pass it via extra_custom_data.",
                agent.id, var, candidate.id,
            )
            custom_data[var] = ""

    for k, v in extra.items():
        custom_data.setdefault(k, v)

    return custom_data


@router.post("/outreach", response_model=List[schemas.CallOut])
def launch_outreach(
    job_id: str,
    payload: schemas.OutreachRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    jd = _get_owned_job(db, job_id, current_user)

    if not payload.agent_id:
        raise HTTPException(
            status_code=400,
            detail="Select an agent before placing a call.",
        )

    agent = db.query(models.Agent).filter(models.Agent.id == payload.agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if agent.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your agent")

    provider_agent_id = agent.hunar_agent_id

    client = HunarClient()

    created_calls: List[models.OutreachCall] = []

    for candidate_id in payload.candidate_ids:
        candidate = db.query(models.Candidate).filter(
            models.Candidate.id == candidate_id, models.Candidate.job_description_id == jd.id
        ).first()
        if not candidate:
            continue
        if not candidate.phone_number:
            raise HTTPException(
                status_code=400,
                detail=f"Candidate '{candidate.full_name}' has no phone number. "
                       f"Add one before initiating a call.",
            )

        request_id = f"job-{jd.id[:8]}-cand-{candidate.id[:8]}-{uuid.uuid4().hex[:6]}"
        custom_data = _build_custom_data(agent, jd, candidate, payload.extra_custom_data)

        call_row = models.OutreachCall(
            candidate_id=candidate.id,
            mobile_number=candidate.phone_number,
            hunar_agent_id=provider_agent_id,
            request_id=request_id,
            status=models.CallStatusEnum.NOT_STARTED,
            triggered_by=current_user.username,
        )

        if client.is_configured:
            logger.info(
                "Placing immediate call: job=%s candidate=%s (%s) agent=%s request_id=%s "
                "custom_data=%s (no retry_config/guardrails sent -> dialed immediately, "
                "no calling-window restriction applied by this app)",
                jd.id, candidate.id, candidate.full_name, provider_agent_id, request_id, custom_data,
            )
            try:
                resp = client.create_call(
                    agent_id=provider_agent_id,
                    callee_name=candidate.full_name,
                    mobile_number=candidate.phone_number,
                    custom_data=custom_data,
                    request_id=request_id,

                )
                call_row.hunar_call_id = resp.get("id")
                call_row.status = _map_status(resp.get("status"))
                logger.info(
                    "Call created OK: job=%s candidate=%s hunar_call_id=%s status=%s",
                    jd.id, candidate.id, resp.get("id"), resp.get("status"),
                )
            except HunarAPIError as exc:
                call_row.status = models.CallStatusEnum.FAILED
                call_row.result = {"error": exc.message, "details": exc.details}
                logger.error(
                    "Call FAILED to place: job=%s candidate=%s (%s) agent=%s "
                    "status_code=%s message=%r details=%s",
                    jd.id, candidate.id, candidate.full_name, provider_agent_id,
                    exc.status_code, exc.message, exc.details,
                )
        else:

            logger.warning(
                "Skipping real call for candidate %s — HUNAR_API_KEY is not set on the "
                "backend, so this app cannot place calls yet.", candidate.id,
            )
            call_row.result = {
                "info": "Calling is not yet configured for this account."
            }

        db.add(call_row)
        created_calls.append(call_row)

    db.commit()
    for c in created_calls:
        db.refresh(c)

    return [_call_out(c) for c in created_calls]


@router.get("/calls", response_model=List[schemas.CallOut])
def list_job_calls(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    jd = _get_owned_job(db, job_id, current_user)
    calls = (
        db.query(models.OutreachCall)
        .join(models.Candidate, models.OutreachCall.candidate_id == models.Candidate.id)
        .filter(models.Candidate.job_description_id == jd.id)
        .order_by(models.OutreachCall.created_at.desc())
        .all()
    )
    return [_call_out(c) for c in calls]


def _map_status(raw: str) -> models.CallStatusEnum:
    try:
        return models.CallStatusEnum(raw)
    except (ValueError, TypeError):
        return models.CallStatusEnum.NOT_STARTED


def _call_out(c: models.OutreachCall) -> schemas.CallOut:
    candidate = c.candidate
    return schemas.CallOut(
        id=c.id,
        candidate_id=c.candidate_id,
        provider_call_id=c.hunar_call_id,
        agent_id=c.hunar_agent_id,
        request_id=c.request_id,
        mobile_number=c.mobile_number,
        status=c.status.value if hasattr(c.status, "value") else c.status,
        lifecycle_status=c.lifecycle_status,
        duration_seconds=c.duration_seconds,
        recording_url=c.recording_url,
        result=c.result or {},
        engagement_status=c.engagement_status,
        answered_by=c.answered_by,
        triggered_by=c.triggered_by,
        guardrails=c.guardrails,
        timezone=c.timezone,
        created_at=c.created_at,
        started_at=c.started_at,
        ended_at=c.ended_at,
        candidate_name=candidate.full_name if candidate else None,
        candidate_title=candidate.title if candidate else None,
        candidate_company=candidate.company if candidate else None,
        job_description_id=candidate.job_description_id if candidate else None,
        job_description_title=candidate.job_description.title if candidate and candidate.job_description else None,
    )
