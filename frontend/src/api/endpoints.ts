import { apiClient } from "./client";
import {
  User,
  JobDescription,
  Candidate,
  Paginated,
  Agent,
  AgentQuestion,
  OutreachCall,
  JobOverview,
  ProviderInfo,
  CallSchedule,
} from "../types";

// ---------- Auth ----------

export async function login(username: string, password: string) {
  const form = new URLSearchParams();
  form.append("username", username);
  form.append("password", password);
  const { data } = await apiClient.post("/api/auth/login", form, {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });
  return data as { access_token: string; token_type: string; user: User };
}

export async function register(username: string, password: string, full_name?: string) {
  const { data } = await apiClient.post("/api/auth/register", { username, password, full_name });
  return data as User;
}

export async function fetchMe() {
  const { data } = await apiClient.get("/api/auth/me");
  return data as User;
}

// ---------- Jobs ----------

export async function listJobs() {
  const { data } = await apiClient.get("/api/jobs");
  return data as JobDescription[];
}

export async function createJob(payload: { title: string; raw_text: string }) {
  const { data } = await apiClient.post("/api/jobs", payload);
  return data as JobDescription;
}

export async function getJob(jobId: string) {
  const { data } = await apiClient.get(`/api/jobs/${jobId}`);
  return data as JobDescription;
}

export async function updateJobCriteria(
  jobId: string,
  payload: Partial<Pick<JobDescription, "keywords" | "locations" | "seniority" | "company_hint">>
) {
  const { data } = await apiClient.patch(`/api/jobs/${jobId}/criteria`, payload);
  return data as JobDescription;
}

export async function deleteJob(jobId: string) {
  await apiClient.delete(`/api/jobs/${jobId}`);
}

// ---------- Search / candidates ----------

export async function getProviders(jobId: string) {
  const { data } = await apiClient.get(`/api/jobs/${jobId}/providers`);
  return data as ProviderInfo[];
}

export async function searchCandidates(
  jobId: string,
  payload: { provider: string; limit?: number; keywords?: string[]; locations?: string[]; seniority?: string }
) {
  const { data } = await apiClient.post(`/api/jobs/${jobId}/search`, payload);
  return data as Paginated<Candidate>;
}

export async function listCandidates(jobId: string, page = 1, pageSize = 20) {
  const { data } = await apiClient.get(`/api/jobs/${jobId}/candidates`, {
    params: { page, page_size: pageSize },
  });
  return data as Paginated<Candidate>;
}

export async function getCandidate(jobId: string, candidateId: string) {
  const { data } = await apiClient.get(`/api/jobs/${jobId}/candidates/${candidateId}`);
  return data as Candidate;
}

export async function updateCandidatePhone(jobId: string, candidateId: string, phone_number: string) {
  const { data } = await apiClient.patch(`/api/jobs/${jobId}/candidates/${candidateId}/phone`, {
    phone_number,
  });
  return data as Candidate;
}

// ---------- Agents ----------

export async function listAgents() {
  const { data } = await apiClient.get("/api/agents");
  return data as Agent[];
}

export interface AgentFormPayload {
  name: string;
  language: string;
  voice_persona: string;
  persona_name?: string;
  objective: string;
  agent_prompt: string;
  introduction: string;
  silence_response?: string;
  conclusion?: string;
  questions: AgentQuestion[];
  description?: string;
  is_active?: boolean;
  company?: string;
}

export async function createAgent(payload: AgentFormPayload) {
  const { data } = await apiClient.post("/api/agents", payload);
  return data as Agent;
}

export async function updateAgent(agentId: string, payload: Partial<AgentFormPayload>) {
  const { data } = await apiClient.patch(`/api/agents/${agentId}`, payload);
  return data as Agent;
}

export async function deleteAgent(agentId: string) {
  await apiClient.delete(`/api/agents/${agentId}`);
}

// ---------- Outreach ----------

export async function launchOutreach(
  jobId: string,
  payload: { candidate_ids: string[]; agent_id: string; extra_custom_data?: Record<string, any> }
) {
  const { data } = await apiClient.post(`/api/jobs/${jobId}/outreach`, payload);
  return data as OutreachCall[];
}

export async function listJobCalls(jobId: string) {
  const { data } = await apiClient.get(`/api/jobs/${jobId}/calls`);
  return data as OutreachCall[];
}

// ---------- Dashboard ----------

export async function listAllCalls(status?: string) {
  const { data } = await apiClient.get(`/api/dashboard/calls`, { params: status ? { status } : {} });
  return data as OutreachCall[];
}

export async function getCallDetail(callId: string) {
  const { data } = await apiClient.get(`/api/dashboard/calls/${callId}`);
  return data as OutreachCall;
}

export async function syncCalls() {
  const { data } = await apiClient.post(`/api/dashboard/calls/sync`);
  return data as OutreachCall[];
}

// ---------- Call schedules ----------

export interface CallScheduleFormPayload {
  candidate_id: string;
  agent_id: string;
  allowed_days: string[];
  earliest_call_time: string;
  last_call_time: string;
  timezone: string;
  notes?: string;
  extra_custom_data?: Record<string, any>;
}

export async function createSchedule(payload: CallScheduleFormPayload) {
  const { data } = await apiClient.post(`/api/schedules`, payload);
  return data as CallSchedule;
}

export async function listSchedules(params?: { status?: string; job_id?: string; candidate_id?: string }) {
  const { data } = await apiClient.get(`/api/schedules`, { params });
  return data as CallSchedule[];
}

export async function getSchedule(scheduleId: string) {
  const { data } = await apiClient.get(`/api/schedules/${scheduleId}`);
  return data as CallSchedule;
}

export async function updateSchedule(scheduleId: string, payload: Partial<CallScheduleFormPayload>) {
  const { data } = await apiClient.put(`/api/schedules/${scheduleId}`, payload);
  return data as CallSchedule;
}

export async function deleteSchedule(scheduleId: string) {
  await apiClient.delete(`/api/schedules/${scheduleId}`);
}

export async function dispatchScheduleNow(scheduleId: string) {
  const { data } = await apiClient.post(`/api/schedules/${scheduleId}/call-now`);
  return data as CallSchedule;
}

export async function getSummary() {
  const { data } = await apiClient.get(`/api/dashboard/summary`);
  return data as {
    job_count: number;
    candidate_count: number;
    call_count: number;
    status_counts: Record<string, number>;
  };
}

export async function getJobsOverview() {
  const { data } = await apiClient.get(`/api/dashboard/jobs-overview`);
  return data as JobOverview[];
}
