import React, { useEffect, useState } from "react";
import * as api from "../api/endpoints";
import { Agent, AgentQuestion } from "../types";
import { LANGUAGE_OPTIONS, VOICE_PERSONA_OPTIONS, ANSWER_TYPE_OPTIONS } from "../constants/agentOptions";

function emptyQuestion(): AgentQuestion {
  return { question: "", answer_key: "", answer_type: "string" };
}

// Sensible starting point for the "Build a new agent" form so a brand-new
// agent is valid and ready to save without the user having to know what
// Hunar expects in every field first. All of this is fully editable.
const DEFAULT_AGENT_PROMPT =
  "You are a friendly, professional recruiter named {persona_name} calling on behalf of {company} " +
  "about the {job_role} role. Keep the conversation natural and concise, listen actively, and ask " +
  "the screening questions one at a time. Stay polite and respectful at all times, and end the call " +
  "gracefully if the candidate isn't interested or asks to be called back later.";

const DEFAULT_INTRODUCTION =
  "Hi {callee_name}, this is {persona_name} calling from {company} about the {job_role} role. " +
  "Do you have a couple of minutes to chat?";

const DEFAULT_SILENCE_RESPONSE = "Hi, are you still there? Take your time — I can wait a moment.";

const DEFAULT_CONCLUSION =
  "Thanks so much for your time today, {callee_name}. We'll be in touch soon with next steps. Have a great day!";

const DEFAULT_OBJECTIVE =
  "Screen inbound candidates for the role: confirm interest, check availability, and capture their " +
  "answers to a short set of qualifying questions.";

function defaultQuestions(): AgentQuestion[] {
  return [
    { question: "Are you currently open to new roles?", answer_key: "open_to_roles", answer_type: "boolean" },
    { question: "What is your notice period, in weeks?", answer_key: "notice_period_weeks", answer_type: "number" },
    { question: "What is your expected salary range?", answer_key: "expected_salary", answer_type: "string" },
  ];
}

function statusChipClass(status?: string | null) {
  if (status === "ACTIVE") return "badge completed";
  if (status === "DRAFT") return "badge warn";
  return "badge not_started";
}

export default function AgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingAgent, setEditingAgent] = useState<Agent | null>(null);

  // Basics
  const [name, setName] = useState("");
  const [language, setLanguage] = useState("ENGLISH");
  const [voicePersona, setVoicePersona] = useState("NEHA");
  const [personaName, setPersonaName] = useState("");
  const [company, setCompany] = useState("");

  // Conversation
  const [objective, setObjective] = useState("");
  const [agentPrompt, setAgentPrompt] = useState("");
  const [introduction, setIntroduction] = useState("");
  const [silenceResponse, setSilenceResponse] = useState("");
  const [conclusion, setConclusion] = useState("");

  // Questions -> structured results
  const [questions, setQuestions] = useState<AgentQuestion[]>([emptyQuestion()]);

  const [description, setDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    const data = await api.listAgents();
    setAgents(data);
    setLoading(false);
  }

  useEffect(() => {
    load();
  }, []);

  function resetForm() {
    setName("");
    setLanguage("ENGLISH");
    setVoicePersona("NEHA");
    setPersonaName("");
    setObjective("");
    setAgentPrompt("");
    setIntroduction("");
    setSilenceResponse("");
    setConclusion("");
    setQuestions([emptyQuestion()]);
    setDescription("");
    setEditingId(null);
    setEditingAgent(null);
    setShowForm(false);
    setError(null);
    setCompany("");
  }

  function startCreate() {
    resetForm();
    // Prefill the conversation fields with a working starting point rather
    // than leaving them blank — the user can edit or replace any of this.
    setObjective(DEFAULT_OBJECTIVE);
    setAgentPrompt(DEFAULT_AGENT_PROMPT);
    setIntroduction(DEFAULT_INTRODUCTION);
    setSilenceResponse(DEFAULT_SILENCE_RESPONSE);
    setConclusion(DEFAULT_CONCLUSION);
    setQuestions(defaultQuestions());
    setShowForm(true);
  }

  function startEdit(agent: Agent) {
    setEditingId(agent.id);
    setEditingAgent(agent);
    setName(agent.name);
    setLanguage(agent.language || "ENGLISH");
    setVoicePersona(agent.voice_persona || "NEHA");
    setPersonaName(agent.persona_name || "");
    setCompany(agent.company || "");
    setObjective(agent.objective || "");
    setAgentPrompt(agent.agent_prompt || "");
    setIntroduction(agent.introduction || "");
    setSilenceResponse(agent.silence_response || "");
    setConclusion(agent.conclusion || "");
    setQuestions(agent.questions && agent.questions.length > 0 ? agent.questions : [emptyQuestion()]);
    setDescription(agent.description || "");
    setError(null);
    setShowForm(true);
  }

  function updateQuestion(index: number, patch: Partial<AgentQuestion>) {
    setQuestions((prev) => prev.map((q, i) => (i === index ? { ...q, ...patch } : q)));
  }

  function addQuestion() {
    setQuestions((prev) => [...prev, emptyQuestion()]);
  }

  function removeQuestion(index: number) {
    setQuestions((prev) => (prev.length > 1 ? prev.filter((_, i) => i !== index) : prev));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);

    const cleanQuestions = questions
      .filter((q) => q.question.trim() && q.answer_key.trim())
      .map((q) => ({ ...q, answer_key: q.answer_key.trim().replace(/\s+/g, "_") }));

    const payload = {
      name,
      language,
      voice_persona: voicePersona,
      persona_name: personaName || undefined,
      company: company || undefined,
      objective,
      agent_prompt: agentPrompt,
      introduction,
      silence_response: silenceResponse || undefined,
      conclusion: conclusion || undefined,
      questions: cleanQuestions,
      description: description || undefined,
    };

    try {
      if (editingId) {
        await api.updateAgent(editingId, payload);
      } else {
        await api.createAgent(payload);
      }
      resetForm();
      await load();
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Failed to save agent. Check that voice calling is configured.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(id: string) {
    if (!confirm("Delete this agent?")) return;
    await api.deleteAgent(id);
    load();
  }

  async function toggleActive(agent: Agent) {
    await api.updateAgent(agent.id, { is_active: !agent.is_active });
    load();
  }

  return (
    <div>
      <div className="flex-between">
        <div>
          <div className="page-title">Agents</div>
          <div className="page-subtitle">
            Build the voice agents used to place outreach calls — no provider agent ID needed, it's created for you.
          </div>
        </div>
        <button className="btn" onClick={() => (showForm ? resetForm() : startCreate())}>
          {showForm ? "Cancel" : "+ Build a new agent"}
        </button>
      </div>

      {showForm && (
        <form className="card mt-16" onSubmit={handleSubmit}>
          {editingAgent && (
            <div className="flex-between mt-16" style={{ marginBottom: 4 }}>
              <div className="muted" style={{ fontSize: 12 }}>
                Provider ID: {editingAgent.provider_agent_id || "—"}
                {editingAgent.agent_code ? ` · Code: ${editingAgent.agent_code}` : ""}
              </div>
              {editingAgent.provider_status && (
                <span className={statusChipClass(editingAgent.provider_status)}>{editingAgent.provider_status}</span>
              )}
            </div>
          )}

          <div className="section-label">Basics</div>
          <div className="grid grid-2">
            <div className="field">
              <label>Agent name</label>
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Recruiting screener"
                minLength={3}
                required
              />
            </div>
            <div className="field">
              <label>Persona display name (optional)</label>
              <input
                value={personaName}
                onChange={(e) => setPersonaName(e.target.value)}
                placeholder="Defaults to the voice persona's name"
              />
           </div>
             <div className="field">
              <label>Company (used for {"{company}"} in the prompt)</label>
              <input value={company} onChange={(e) => setCompany(e.target.value)} placeholder="e.g. Acme Corp" />
              <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>
               Fills the <code>{"{company}"}</code> variable on every call this agent makes. Leave blank to fall back
               to the candidate's own company instead.
              </div>
           </div>
          </div>
          <div className="grid grid-2">
            <div className="field">
              <label>Language</label>
              <select value={language} onChange={(e) => setLanguage(e.target.value)}>
                {LANGUAGE_OPTIONS.map((l) => (
                  <option key={l} value={l}>
                    {l.charAt(0) + l.slice(1).toLowerCase()}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label>Voice persona</label>
              <select value={voicePersona} onChange={(e) => setVoicePersona(e.target.value)}>
                {VOICE_PERSONA_OPTIONS.map((v) => (
                  <option key={v} value={v}>
                    {v.charAt(0) + v.slice(1).toLowerCase()}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="section-label">Conversation</div>
          <div className="field">
            <label>Objective</label>
            <textarea
              value={objective}
              onChange={(e) => setObjective(e.target.value)}
              rows={2}
              placeholder="The business objective that guides the agent's responses, e.g. qualify candidates for a role and gauge interest."
              required
            />
          </div>
          <div className="field">
            <label>Agent prompt</label>
            <textarea
              value={agentPrompt}
              onChange={(e) => setAgentPrompt(e.target.value)}
              rows={4}
              placeholder="You are a friendly recruiter calling to screen candidates for {job_role}…"
              required
            />
          </div>
          <div className="field">
            <label>Introduction (opening line)</label>
            <textarea
              value={introduction}
              onChange={(e) => setIntroduction(e.target.value)}
              rows={2}
              placeholder="Hi {callee_name}, this is {persona_name} calling about the {job_role} role…"
              required
            />
          </div>
          <div className="grid grid-2">
            <div className="field">
              <label>Silence response (optional)</label>
              <textarea
                value={silenceResponse}
                onChange={(e) => setSilenceResponse(e.target.value)}
                rows={2}
                placeholder="Hi, are you still there?"
              />
            </div>
            <div className="field">
              <label>Conclusion (optional)</label>
              <textarea
                value={conclusion}
                onChange={(e) => setConclusion(e.target.value)}
                rows={2}
                placeholder="Thanks for your time. Have a great day!"
              />
            </div>
          </div>

          <div className="section-label">Questions to capture</div>
          <div className="muted" style={{ fontSize: 13, marginBottom: 10 }}>
            Each question you add becomes a structured field pulled from the call's results — this is what
            shows up clearly on the dashboard for every call.
          </div>
          {questions.map((q, i) => (
            <div className="question-row" key={i}>
              <div className="field">
                {i === 0 && <label>Question</label>}
                <input
                  value={q.question}
                  onChange={(e) => updateQuestion(i, { question: e.target.value })}
                  placeholder="Are you currently open to new roles?"
                />
              </div>
              <div className="field">
                {i === 0 && <label>Field name</label>}
                <input
                  value={q.answer_key}
                  onChange={(e) => updateQuestion(i, { answer_key: e.target.value })}
                  placeholder="open_to_roles"
                />
              </div>
              <div className="field">
                {i === 0 && <label>Answer type</label>}
                <select
                  value={q.answer_type}
                  onChange={(e) => updateQuestion(i, { answer_type: e.target.value as AgentQuestion["answer_type"] })}
                >
                  {ANSWER_TYPE_OPTIONS.map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </select>
              </div>
              <button
                type="button"
                className="btn secondary small"
                style={{ marginTop: i === 0 ? 22 : 0 }}
                onClick={() => removeQuestion(i)}
              >
                Remove
              </button>
            </div>
          ))}
          <button type="button" className="btn secondary small mt-16" onClick={addQuestion}>
            + Add question
          </button>

          <div className="section-label">Internal notes</div>
          <div className="field">
            <label>Description (only visible to you, not sent to the agent)</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
              placeholder="What this agent is for…"
            />
          </div>

          {error && <div className="error-text">{error}</div>}

          <button className="btn mt-16" type="submit" disabled={submitting}>
            {submitting ? "Saving…" : editingId ? "Save changes" : "Create agent"}
          </button>
        </form>
      )}

      <div className="mt-24">
        {loading ? (
          <div className="muted">Loading…</div>
        ) : agents.length === 0 ? (
          <div className="card muted">No agents configured yet. Build one to start placing calls.</div>
        ) : (
          agents.map((a) => (
            <div className="agent-card" key={a.id}>
              <div className="agent-card-head">
                <div>
                  <div style={{ fontWeight: 700, fontSize: 15 }}>{a.name}</div>
                  <div className="muted" style={{ fontSize: 13, marginTop: 2 }}>
                    {a.objective || a.description || "No objective set."}
                  </div>
                </div>
                <div className="flex gap-8">
                  <button className="btn secondary small" onClick={() => startEdit(a)}>
                    Edit
                  </button>
                  <button className="btn danger small" onClick={() => handleDelete(a.id)}>
                    Delete
                  </button>
                </div>
              </div>
              <div className="agent-meta">
                <span className="chip">{a.language}</span>
                <span className="chip">{a.persona_name || a.voice_persona}</span>
                <span className="chip">{a.questions?.length || 0} questions</span>
                {a.provider_status && <span className={statusChipClass(a.provider_status)}>{a.provider_status}</span>}
                <span
                  className={`chip ${a.is_active ? "" : "muted"}`}
                  style={{ cursor: "pointer" }}
                  onClick={() => toggleActive(a)}
                >
                  {a.is_active ? "Active in this app" : "Inactive in this app"}
                </span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
