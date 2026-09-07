import logging
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.deps import get_current_user
from app.services.hunar_client import HunarClient, HunarAPIError

logger = logging.getLogger("app.agents")

router = APIRouter(prefix="/api/agents", tags=["agents"])


def _build_result_fields(payload: schemas.AgentCreate) -> Dict[str, Any]:
    """
    Turn the friendly question builder into the `result_prompt` /
    `result_schema` pair the Hunar API expects. If the caller supplied those
    directly (advanced use), those win instead.
    """
    if payload.result_schema is not None:
        result_schema = payload.result_schema
    else:
        result_schema = {q.answer_key: q.answer_type for q in payload.questions}

    if payload.result_prompt:
        result_prompt = payload.result_prompt
    elif payload.questions:
        lines = "\n".join(f"- {q.answer_key}: {q.question}" for q in payload.questions)
        result_prompt = (
            "Analyze the conversation and extract the following fields:\n" + lines
        )
    else:
        result_prompt = "Summarize the outcome of the conversation."

    return {"result_prompt": result_prompt, "result_schema": result_schema}


def _hunar_payload(payload: schemas.AgentCreate) -> Dict[str, Any]:
    result_fields = _build_result_fields(payload)
    data: Dict[str, Any] = {
        "name": payload.name,
        "language": payload.language,
        "voice_persona": payload.voice_persona,
        "agent_prompt": payload.agent_prompt,
        "objective": payload.objective,
        "introduction": payload.introduction,
        **result_fields,
    }
    if payload.persona_name:
        data["persona_name"] = payload.persona_name
    return data


def _apply_local_fields(agent: models.Agent, payload: schemas.AgentCreate, result_fields: Dict[str, Any]) -> None:
    agent.name = payload.name
    agent.language = payload.language
    agent.voice_persona = payload.voice_persona
    agent.persona_name = payload.persona_name
    agent.objective = payload.objective
    agent.agent_prompt = payload.agent_prompt
    agent.introduction = payload.introduction
    agent.silence_response = payload.silence_response
    agent.conclusion = payload.conclusion
    agent.questions = [q.model_dump() for q in payload.questions]
    agent.result_prompt = result_fields["result_prompt"]
    agent.result_schema = result_fields["result_schema"]
    agent.description = payload.description
    agent.is_active = payload.is_active
    agent.company = payload.company


def _apply_hunar_response(agent: models.Agent, data: Dict[str, Any]) -> None:
    agent.hunar_agent_id = data.get("id") or agent.hunar_agent_id
    agent.provider_status = data.get("status") or agent.provider_status
    agent.agent_code = data.get("agent_code") or agent.agent_code
    agent.custom_variables = data.get("custom_variables") or agent.custom_variables or []


def _to_out(agent: models.Agent) -> schemas.AgentOut:
    return schemas.AgentOut(
        id=agent.id,
        name=agent.name,
        provider_agent_id=agent.hunar_agent_id,
        language=agent.language or "ENGLISH",
        voice_persona=agent.voice_persona or "NEHA",
        persona_name=agent.persona_name,
        company=agent.company,
        objective=agent.objective,
        agent_prompt=agent.agent_prompt,
        introduction=agent.introduction,
        silence_response=agent.silence_response,
        conclusion=agent.conclusion,
        questions=agent.questions or [],
        result_prompt=agent.result_prompt,
        result_schema=agent.result_schema or {},
        custom_variables=agent.custom_variables or [],
        provider_status=agent.provider_status,
        agent_code=agent.agent_code,
        description=agent.description,
        config=agent.config or {},
        is_active=agent.is_active,
        created_at=agent.created_at,
    )


def _get_owned_agent(db: Session, agent_id: str, current_user: models.User) -> models.Agent:
    agent = db.query(models.Agent).filter(models.Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if agent.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your agent")
    return agent


@router.post("", response_model=schemas.AgentOut, status_code=201)
def create_agent(
    payload: schemas.AgentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Creates the agent directly on Hunar (POST /agents/) from the fields the
    user filled in on the "Build Your Agent" screen -- there is no "Agent ID"
    field for them to fill in themselves. The id Hunar returns is stored
    automatically so the agent can be used to place calls right away.
    """
    client = HunarClient()
    if not client.is_configured:
        raise HTTPException(
            status_code=400,
            detail="Voice calling isn't configured yet. Set HUNAR_API_KEY on the backend first.",
        )

    result_fields = _build_result_fields(payload)
    logger.info("Creating Hunar agent '%s' for user %s", payload.name, current_user.username)
    try:
        hunar_agent = client.create_agent(_hunar_payload(payload))
    except HunarAPIError as exc:
        logger.error(
            "Agent creation FAILED for user %s: status_code=%s message=%r details=%s",
            current_user.username, exc.status_code, exc.message, exc.details,
        )
        raise HTTPException(status_code=exc.status_code if exc.status_code in (400, 401, 402, 404, 422) else 502,
                             detail=exc.message)

    agent = models.Agent(owner_id=current_user.id)
    _apply_local_fields(agent, payload, result_fields)
    _apply_hunar_response(agent, hunar_agent)

    db.add(agent)
    db.commit()
    db.refresh(agent)
    logger.info(
        "Agent created OK: local_id=%s hunar_agent_id=%s custom_variables=%s",
        agent.id, agent.hunar_agent_id, agent.custom_variables,
    )
    return _to_out(agent)


@router.get("", response_model=List[schemas.AgentOut])
def list_agents(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    agents = (
        db.query(models.Agent)
        .filter(models.Agent.owner_id == current_user.id)
        .order_by(models.Agent.created_at.desc())
        .all()
    )
    return [_to_out(a) for a in agents]


@router.get("/{agent_id}", response_model=schemas.AgentOut)
def get_agent(
    agent_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    agent = _get_owned_agent(db, agent_id, current_user)
    return _to_out(agent)


@router.patch("/{agent_id}", response_model=schemas.AgentOut)
def update_agent(
    agent_id: str,
    payload: schemas.AgentUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    agent = _get_owned_agent(db, agent_id, current_user)

    # Merge the incoming partial update onto the agent's current values, then
    # push the *complete* set of fields to Hunar. This sidesteps Hunar's rule
    # that changing voice_persona/language requires every other field to be
    # resent too -- we always have the full picture stored locally.
    merged = schemas.AgentCreate(
        name=payload.name if payload.name is not None else agent.name,
        language=payload.language if payload.language is not None else (agent.language or "ENGLISH"),
        voice_persona=payload.voice_persona if payload.voice_persona is not None else (agent.voice_persona or "NEHA"),
        persona_name=payload.persona_name if payload.persona_name is not None else agent.persona_name,
        company=payload.company if payload.company is not None else agent.company,
        objective=payload.objective if payload.objective is not None else (agent.objective or ""),
        agent_prompt=payload.agent_prompt if payload.agent_prompt is not None else (agent.agent_prompt or ""),
        introduction=payload.introduction if payload.introduction is not None else (agent.introduction or ""),
        silence_response=payload.silence_response if payload.silence_response is not None else agent.silence_response,
        conclusion=payload.conclusion if payload.conclusion is not None else agent.conclusion,
        questions=payload.questions if payload.questions is not None else (agent.questions or []),
        result_prompt=payload.result_prompt if payload.result_prompt is not None else agent.result_prompt,
        result_schema=payload.result_schema if payload.result_schema is not None else agent.result_schema,
        description=payload.description if payload.description is not None else agent.description,
        is_active=payload.is_active if payload.is_active is not None else agent.is_active,
    )

    result_fields = _build_result_fields(merged)

    client = HunarClient()
    if agent.hunar_agent_id and client.is_configured:
        logger.info("Updating Hunar agent %s (%s)", agent.id, agent.hunar_agent_id)
        try:
            hunar_agent = client.update_agent(agent.hunar_agent_id, _hunar_payload(merged))
            _apply_hunar_response(agent, hunar_agent)
        except HunarAPIError as exc:
            logger.error(
                "Agent update FAILED for agent %s (%s): status_code=%s message=%r details=%s",
                agent.id, agent.hunar_agent_id, exc.status_code, exc.message, exc.details,
            )
            raise HTTPException(status_code=exc.status_code if exc.status_code in (400, 401, 402, 404, 422) else 502,
                                 detail=exc.message)

    _apply_local_fields(agent, merged, result_fields)
    db.commit()
    db.refresh(agent)
    return _to_out(agent)


@router.delete("/{agent_id}", status_code=204)
def delete_agent(
    agent_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    agent = _get_owned_agent(db, agent_id, current_user)
    db.delete(agent)
    db.commit()
    return None
