from datetime import datetime
from typing import Generic, List, Optional, Dict, Any, TypeVar

from pydantic import BaseModel, Field, ConfigDict

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int


# ---------- Auth ----------

class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=6, max_length=128)
    full_name: Optional[str] = None


class UserOut(BaseModel):
    id: str
    username: str
    full_name: Optional[str] = None

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------- Job Description ----------

class JobDescriptionCreate(BaseModel):
    title: str
    raw_text: str
    # Optional manual overrides; if omitted, will be auto-parsed from raw_text
    keywords: Optional[List[str]] = None
    locations: Optional[List[str]] = None
    seniority: Optional[str] = None
    company_hint: Optional[str] = None


class JobDescriptionUpdateCriteria(BaseModel):
    keywords: Optional[List[str]] = None
    locations: Optional[List[str]] = None
    seniority: Optional[str] = None
    company_hint: Optional[str] = None


class JobDescriptionOut(BaseModel):
    id: str
    title: str
    raw_text: str
    keywords: List[str] = []
    locations: List[str] = []
    seniority: Optional[str] = None
    company_hint: Optional[str] = None
    created_at: datetime
    candidate_count: int = 0

    class Config:
        from_attributes = True


# ---------- Candidate / Search ----------

class SearchRequest(BaseModel):
    provider: str  # PDL | APOLLO | PROXYCURL | CORESIGNAL | MOCK
    limit: int = 15
    # optional ad-hoc overrides of the JD's stored criteria for this search
    keywords: Optional[List[str]] = None
    locations: Optional[List[str]] = None
    seniority: Optional[str] = None


class CandidateOut(BaseModel):
    id: str
    job_description_id: str
    source_provider: str
    external_id: Optional[str] = None
    full_name: str
    title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    linkedin_url: Optional[str] = None
    email: Optional[str] = None
    phone_number: Optional[str] = None
    skills: List[str] = []
    created_at: datetime
    latest_call_status: Optional[str] = None
    latest_call_id: Optional[str] = None

    class Config:
        from_attributes = True


class PaginatedCandidates(Page[CandidateOut]):
    pass


class CandidatePhoneUpdate(BaseModel):
    phone_number: str


# ---------- Agents ----------

class AgentQuestion(BaseModel):
    """
    One row in the "Build Your Agent" question builder. `answer_key` becomes
    a field name in the Hunar `result_schema`; `answer_type` controls what
    kind of value is captured for it.
    """
    question: str = Field(min_length=1, max_length=500)
    answer_key: str = Field(min_length=1, max_length=64)
    answer_type: str = Field(default="string")  # string | boolean | number


class AgentCreate(BaseModel):
    name: str = Field(min_length=3, max_length=64)
    language: str = "ENGLISH"
    voice_persona: str = "NEHA"
    persona_name: Optional[str] = None
    company: Optional[str] = None
    objective: str = Field(min_length=1)
    agent_prompt: str = Field(min_length=1)
    introduction: str = Field(min_length=1)
    silence_response: Optional[str] = None
    conclusion: Optional[str] = None
    # Either provide plain questions (recommended, matches the on-screen
    # builder) or a hand-written result_prompt/result_schema directly.
    questions: List[AgentQuestion] = []
    result_prompt: Optional[str] = None
    result_schema: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    is_active: bool = True


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    language: Optional[str] = None
    voice_persona: Optional[str] = None
    persona_name: Optional[str] = None
    company: Optional[str] = None 
    objective: Optional[str] = None
    agent_prompt: Optional[str] = None
    introduction: Optional[str] = None
    silence_response: Optional[str] = None
    conclusion: Optional[str] = None
    questions: Optional[List[AgentQuestion]] = None
    result_prompt: Optional[str] = None
    result_schema: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class AgentOut(BaseModel):
    id: str
    name: str
    provider_agent_id: Optional[str] = None
    language: str = "ENGLISH"
    voice_persona: str = "NEHA"
    persona_name: Optional[str] = None
    company: Optional[str] = None 
    objective: Optional[str] = None
    agent_prompt: Optional[str] = None
    introduction: Optional[str] = None
    silence_response: Optional[str] = None
    conclusion: Optional[str] = None
    questions: List[AgentQuestion] = []
    result_prompt: Optional[str] = None
    result_schema: Dict[str, Any] = {}
    custom_variables: List[str] = []
    provider_status: Optional[str] = None
    agent_code: Optional[str] = None
    description: Optional[str] = None
    config: Dict[str, Any] = {}
    is_active: bool = True
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- Outreach / Calls ----------

class OutreachRequest(BaseModel):
    candidate_ids: List[str]
    agent_id: str  # id of one of the current user's Agent rows (see /api/agents)
    extra_custom_data: Optional[Dict[str, Any]] = None


class CallOut(BaseModel):
    id: str
    candidate_id: str
    provider_call_id: Optional[str] = None
    agent_id: Optional[str] = None
    request_id: Optional[str] = None
    mobile_number: str
    status: str
    lifecycle_status: Optional[str] = None
    duration_seconds: Optional[float] = None
    recording_url: Optional[str] = None
    result: Dict[str, Any] = {}
    engagement_status: Optional[str] = None
    answered_by: Optional[str] = None
    triggered_by: Optional[str] = None
    guardrails: Optional[Dict[str, Any]] = None
    timezone: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None

    # denormalized candidate info for dashboard convenience
    candidate_name: Optional[str] = None
    candidate_title: Optional[str] = None
    candidate_company: Optional[str] = None
    job_description_id: Optional[str] = None
    job_description_title: Optional[str] = None

    class Config:
        from_attributes = True


# ---------- Call Schedules ----------

class CallScheduleCreate(BaseModel):
    candidate_id: str
    agent_id: str
    allowed_days: List[str] = Field(min_length=3)
    earliest_call_time: str
    last_call_time: str
    timezone: str = "Asia/Kolkata"
    notes: Optional[str] = None
    extra_custom_data: Optional[Dict[str, Any]] = None


class CallScheduleUpdate(BaseModel):
    agent_id: Optional[str] = None
    allowed_days: Optional[List[str]] = None
    earliest_call_time: Optional[str] = None
    last_call_time: Optional[str] = None
    timezone: Optional[str] = None
    notes: Optional[str] = None
    extra_custom_data: Optional[Dict[str, Any]] = None


class CallScheduleOut(BaseModel):
    id: str
    candidate_id: str
    candidate_name: Optional[str] = None
    candidate_title: Optional[str] = None
    candidate_company: Optional[str] = None
    candidate_phone: Optional[str] = None
    job_description_id: Optional[str] = None
    job_description_title: Optional[str] = None
    agent_id: str
    agent_name: Optional[str] = None
    allowed_days: List[str] = []
    earliest_call_time: str
    last_call_time: str
    timezone: str
    notes: Optional[str] = None
    extra_custom_data: Dict[str, Any] = {}
    status: str
    failure_reason: Optional[str] = None
    outreach_call_id: Optional[str] = None
    outreach_call_status: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ---------- Dashboard ----------

class JobOverviewOut(BaseModel):
    job_id: str
    title: str
    candidate_count: int
    calls: List[CallOut] = []
