import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Text, DateTime, ForeignKey, Enum, Float, Boolean, JSON, Integer
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    username = Column(String(64), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(128), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    job_descriptions = relationship("JobDescription", back_populates="owner")
    agents = relationship("Agent", back_populates="owner", cascade="all, delete-orphan")
    schedules = relationship("CallSchedule", back_populates="owner", cascade="all, delete-orphan")


class Agent(Base):
    """
    A user-configured voice agent. The agent is created directly through the
    Hunar API (POST /agents/) from the fields below -- the user never types a
    provider agent id by hand. hunar_agent_id is the id Hunar returns, stored
    here purely so we can place calls and push updates later.
    """
    __tablename__ = "agents"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    owner_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)

    name = Column(String(255), nullable=False)
    hunar_agent_id = Column(String(128), nullable=True)
    description = Column(Text, nullable=True)
    config = Column(JSON, default=dict)  # voice/config settings, provider-specific
    company = Column(String(255), nullable=True)

    # ---- Fields mirrored from the "Build Your Agent" screen ----
    language = Column(String(32), default="ENGLISH")
    voice_persona = Column(String(32), default="NEHA")
    persona_name = Column(String(64), nullable=True)
    objective = Column(Text, nullable=True)
    agent_prompt = Column(Text, nullable=True)
    introduction = Column(Text, nullable=True)
    silence_response = Column(Text, nullable=True)
    conclusion = Column(Text, nullable=True)
    result_prompt = Column(Text, nullable=True)
    result_schema = Column(JSON, default=dict)
    # The friendly Q&A the user typed into the builder; result_schema and
    # result_prompt are derived from this, but the originals are kept too so
    # editing an agent later is round-trippable.
    questions = Column(JSON, default=list)

    # ---- Fields echoed back from Hunar after create/update ----
    provider_status = Column(String(32), nullable=True)  # DRAFT | ACTIVE
    agent_code = Column(String(64), nullable=True)
    custom_variables = Column(JSON, default=list)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="agents")


class ProviderEnum(str, enum.Enum):
    PDL = "PDL"
    APOLLO = "APOLLO"
    PROXYCURL = "PROXYCURL"
    CORESIGNAL = "CORESIGNAL"
    MOCK = "MOCK"


class JobDescription(Base):
    __tablename__ = "job_descriptions"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    title = Column(String(255), nullable=False)
    raw_text = Column(Text, nullable=False)

    # Parsed / editable search criteria
    keywords = Column(JSON, default=list)          # list[str] skills / role keywords
    locations = Column(JSON, default=list)         # list[str]
    seniority = Column(String(64), nullable=True)
    company_hint = Column(String(255), nullable=True)

    owner_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="job_descriptions")
    candidates = relationship("Candidate", back_populates="job_description", cascade="all, delete-orphan")


class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    job_description_id = Column(UUID(as_uuid=False), ForeignKey("job_descriptions.id"), nullable=False)

    source_provider = Column(Enum(ProviderEnum), nullable=False)
    external_id = Column(String(255), nullable=True)  # id from the provider

    full_name = Column(String(255), nullable=False)
    title = Column(String(255), nullable=True)
    company = Column(String(255), nullable=True)
    location = Column(String(255), nullable=True)
    linkedin_url = Column(String(512), nullable=True)
    email = Column(String(255), nullable=True)
    phone_number = Column(String(64), nullable=True)  # E.164, needed to place a call
    skills = Column(JSON, default=list)
    raw_profile = Column(JSON, default=dict)  # full raw payload from provider, for reference

    created_at = Column(DateTime, default=datetime.utcnow)

    job_description = relationship("JobDescription", back_populates="candidates")
    calls = relationship("OutreachCall", back_populates="candidate", cascade="all, delete-orphan")
    schedules = relationship("CallSchedule", back_populates="candidate", cascade="all, delete-orphan")


class CallStatusEnum(str, enum.Enum):
    NOT_STARTED = "NOT_STARTED"
    SCHEDULED = "SCHEDULED"
    INITIATED = "INITIATED"
    RINGING = "RINGING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    NOT_CONNECTED = "NOT_CONNECTED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


class OutreachCall(Base):
    __tablename__ = "outreach_calls"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    candidate_id = Column(UUID(as_uuid=False), ForeignKey("candidates.id"), nullable=False)

    # DB column names kept for backward compatibility; exposed to the
    # frontend under neutral names (provider_call_id / agent_id) via schemas.py
    hunar_call_id = Column(String(128), unique=True, nullable=True, index=True)
    hunar_agent_id = Column(String(128), nullable=True)
    request_id = Column(String(128), nullable=True, index=True)

    mobile_number = Column(String(64), nullable=False)
    status = Column(Enum(CallStatusEnum), default=CallStatusEnum.NOT_STARTED)
    lifecycle_status = Column(String(32), nullable=True)

    duration_seconds = Column(Float, nullable=True)
    recording_url = Column(String(512), nullable=True)
    result = Column(JSON, default=dict)        # structured Q&A / result_schema answers
    engagement_status = Column(String(32), nullable=True)
    answered_by = Column(String(32), nullable=True)

    # Calling-window settings this call was placed with, when it came from a
    # CallSchedule (see below). None for immediate ("call now") calls, which
    # intentionally omit guardrails so Hunar's org default / immediate
    # dialing applies. Kept purely for display -- Hunar echoes these back on
    # GET but we store our own copy so the UI has them even before a sync.
    guardrails = Column(JSON, nullable=True)
    timezone = Column(String(64), nullable=True)

    triggered_by = Column(String(128), nullable=True)  # username who launched the call
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    candidate = relationship("Candidate", back_populates="calls")
    schedule = relationship("CallSchedule", back_populates="outreach_call", uselist=False)


class ScheduleStatusEnum(str, enum.Enum):
    PENDING = "PENDING"        # saved locally, waiting for its calling window
    DISPATCHED = "DISPATCHED"  # handed off to Hunar; see outreach_call for live status
    CANCELLED = "CANCELLED"    # cancelled by the user before it was ever dispatched
    FAILED = "FAILED"          # Hunar rejected the call when we tried to dispatch it


class CallSchedule(Base):
    """
    A locally-held "call this candidate within this window" intent. Nothing
    is sent to Hunar until the schedule's window opens (checked by the
    background dispatcher in app.main) or the user hits "Call now" on it.
    Because dispatch is entirely under this app's control, a PENDING
    schedule can be freely edited or deleted -- that's the one place calling
    can be reliably "cut" before it ever starts, since Hunar's API has no
    cancel-in-flight endpoint (see OutreachCall.cancelled_at above).
    """
    __tablename__ = "call_schedules"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    owner_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    candidate_id = Column(UUID(as_uuid=False), ForeignKey("candidates.id"), nullable=False)
    agent_id = Column(UUID(as_uuid=False), ForeignKey("agents.id"), nullable=False)

    # Calling-window (mirrors Hunar's `guardrails` request object exactly, so
    # it can be forwarded as-is when the schedule is dispatched).
    allowed_days = Column(JSON, default=list)     # subset of MON..SUN, >=3 distinct
    earliest_call_time = Column(String(5), nullable=False)  # "HH:MM"
    last_call_time = Column(String(5), nullable=False)      # "HH:MM"
    timezone = Column(String(64), default="Asia/Kolkata")

    notes = Column(Text, nullable=True)
    extra_custom_data = Column(JSON, default=dict)

    status = Column(Enum(ScheduleStatusEnum), default=ScheduleStatusEnum.PENDING)
    failure_reason = Column(Text, nullable=True)

    outreach_call_id = Column(UUID(as_uuid=False), ForeignKey("outreach_calls.id"), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User", back_populates="schedules")
    candidate = relationship("Candidate", back_populates="schedules")
    agent = relationship("Agent")
    outreach_call = relationship("OutreachCall", back_populates="schedule")
