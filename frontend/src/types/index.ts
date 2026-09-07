export interface User {
  id: string;
  username: string;
  full_name?: string | null;
}

export interface JobDescription {
  id: string;
  title: string;
  raw_text: string;
  keywords: string[];
  locations: string[];
  seniority?: string | null;
  company_hint?: string | null;
  created_at: string;
  candidate_count: number;
}

export interface Candidate {
  id: string;
  job_description_id: string;
  source_provider: string;
  external_id?: string | null;
  full_name: string;
  title?: string | null;
  company?: string | null;
  location?: string | null;
  linkedin_url?: string | null;
  email?: string | null;
  phone_number?: string | null;
  skills: string[];
  created_at: string;
  latest_call_status?: string | null;
  latest_call_id?: string | null;
}

export interface Paginated<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface AgentQuestion {
  question: string;
  answer_key: string;
  answer_type: "string" | "boolean" | "number";
}

export interface Agent {
  id: string;
  name: string;
  provider_agent_id?: string | null;
  language: string;
  voice_persona: string;
  persona_name?: string | null;
  objective?: string | null;
  agent_prompt?: string | null;
  introduction?: string | null;
  silence_response?: string | null;
  conclusion?: string | null;
  questions: AgentQuestion[];
  result_prompt?: string | null;
  result_schema: Record<string, any>;
  custom_variables: string[];
  provider_status?: string | null;
  agent_code?: string | null;
  description?: string | null;
  config: Record<string, any>;
  is_active: boolean;
  created_at: string;
  company?: string | null;
}

export interface OutreachCall {
  id: string;
  candidate_id: string;
  provider_call_id?: string | null;
  agent_id?: string | null;
  request_id?: string | null;
  mobile_number: string;
  status: string;
  lifecycle_status?: string | null;
  duration_seconds?: number | null;
  recording_url?: string | null;
  result: Record<string, any>;
  engagement_status?: string | null;
  answered_by?: string | null;
  triggered_by?: string | null;
  guardrails?: CallingWindow | null;
  timezone?: string | null;
  created_at: string;
  started_at?: string | null;
  ended_at?: string | null;
  candidate_name?: string | null;
  candidate_title?: string | null;
  candidate_company?: string | null;
  job_description_id?: string | null;
  job_description_title?: string | null;
}

export interface JobOverview {
  job_id: string;
  title: string;
  candidate_count: number;
  calls: OutreachCall[];
}

export interface ProviderInfo {
  id: string;
  configured: boolean;
}

// The set of days/times a scheduled call is allowed to actually ring —
// mirrors Hunar's `guardrails` object exactly.
export interface CallingWindow {
  allowed_days: string[];
  earliest_call_time: string;
  last_call_time: string;
}

export interface CallSchedule {
  id: string;
  candidate_id: string;
  candidate_name?: string | null;
  candidate_title?: string | null;
  candidate_company?: string | null;
  candidate_phone?: string | null;
  job_description_id?: string | null;
  job_description_title?: string | null;
  agent_id: string;
  agent_name?: string | null;
  allowed_days: string[];
  earliest_call_time: string;
  last_call_time: string;
  timezone: string;
  notes?: string | null;
  extra_custom_data: Record<string, any>;
  status: "PENDING" | "DISPATCHED" | "CANCELLED" | "FAILED" | string;
  failure_reason?: string | null;
  outreach_call_id?: string | null;
  outreach_call_status?: string | null;
  created_at: string;
  updated_at: string;
}
