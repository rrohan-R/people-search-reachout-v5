import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import * as api from "../api/endpoints";
import { JobDescription, Candidate, ProviderInfo, Agent } from "../types";
import StatusBadge from "../components/StatusBadge";

// Generic, user-facing labels for search sources (no vendor names shown in the UI).
const PROVIDER_LABELS: Record<string, string> = {
  PDL: "Search source A",
  APOLLO: "Search source B",
  PROXYCURL: "Search source C",
  CORESIGNAL: "Search source D",
  MOCK: "Demo data",
};

const PAGE_SIZE = 20;

export default function JobDetailPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const [job, setJob] = useState<JobDescription | null>(null);
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalCandidates, setTotalCandidates] = useState(0);
  const [providers, setProviders] = useState<ProviderInfo[]>([]);
  const [provider, setProvider] = useState("PDL");
  const [searching, setSearching] = useState(false);
  const [callingIds, setCallingIds] = useState<Set<string>>(new Set());
  const [message, setMessage] = useState<string | null>(null);
  const [messageIsError, setMessageIsError] = useState(false);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [agentId, setAgentId] = useState("");

  // editable criteria
  const [keywordsText, setKeywordsText] = useState("");
  const [locationsText, setLocationsText] = useState("");
  const [seniority, setSeniority] = useState("");
  const [savingCriteria, setSavingCriteria] = useState(false);

  async function loadCandidates(targetPage: number) {
    if (!jobId) return;
    const result = await api.listCandidates(jobId, targetPage, PAGE_SIZE);
    setCandidates(result.items);
    setPage(result.page);
    setTotalPages(result.total_pages);
    setTotalCandidates(result.total);
  }

  async function loadAll() {
    if (!jobId) return;
    const [j, provs, agentList] = await Promise.all([
      api.getJob(jobId),
      api.getProviders(jobId),
      api.listAgents(),
    ]);
    setJob(j);
    setProviders(provs);
    setAgents(agentList);
    const activeAgents = agentList.filter((a) => a.is_active);
    setAgentId(activeAgents[0]?.id || "");
    setKeywordsText(j.keywords.join(", "));
    setLocationsText(j.locations.join(", "));
    setSeniority(j.seniority || "");
    await loadCandidates(1);
  }

  useEffect(() => {
    loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobId]);

  async function saveCriteria() {
    if (!jobId) return;
    setSavingCriteria(true);
    try {
      const updated = await api.updateJobCriteria(jobId, {
        keywords: keywordsText.split(",").map((s) => s.trim()).filter(Boolean),
        locations: locationsText.split(",").map((s) => s.trim()).filter(Boolean),
        seniority: seniority || undefined,
      });
      setJob(updated);
    } finally {
      setSavingCriteria(false);
    }
  }

  async function runSearch() {
    if (!jobId) return;
    setSearching(true);
    setMessage(null);
    try {
      const results = await api.searchCandidates(jobId, { provider, limit: 15 });
      setMessage(`Found ${results.items.length} candidates via ${PROVIDER_LABELS[provider] || provider}.`);
      await loadCandidates(1);
    } catch (err: any) {
      setMessage(err?.response?.data?.detail || "Search failed");
    } finally {
      setSearching(false);
    }
  }

  async function updatePhone(candidateId: string, phone: string) {
    if (!jobId) return;
    const updated = await api.updateCandidatePhone(jobId, candidateId, phone);
    setCandidates((prev) => prev.map((c) => (c.id === candidateId ? updated : c)));
  }

  // Places a single immediate call to one candidate — no scheduling window,
  // no batching. Dials right away using the currently selected agent.
  async function callNow(candidate: Candidate) {
    if (!jobId) return;
    if (!agentId) {
      setMessageIsError(true);
      setMessage("Select an agent before placing a call.");
      return;
    }
    if (!candidate.phone_number) {
      setMessageIsError(true);
      setMessage(`Add a phone number for ${candidate.full_name} before calling.`);
      return;
    }
    setCallingIds((prev) => new Set(prev).add(candidate.id));
    setMessage(null);
    try {
      const calls = await api.launchOutreach(jobId, { candidate_ids: [candidate.id], agent_id: agentId });
      const call = calls[0];
      if (call && (call.status === "FAILED" || call.status === "NOT_CONNECTED")) {
        setMessageIsError(true);
        const errDetail = (call.result as any)?.error || (call.result as any)?.info;
        setMessage(`Call to ${candidate.full_name} failed: ${errDetail || "see server logs for details."}`);
      } else {
        setMessageIsError(false);
        setMessage(`Calling ${candidate.full_name} now. Track it in Conversations.`);
      }
      await loadCandidates(page);
    } catch (err: any) {
      setMessageIsError(true);
      setMessage(err?.response?.data?.detail || `Failed to call ${candidate.full_name}`);
    } finally {
      setCallingIds((prev) => {
        const next = new Set(prev);
        next.delete(candidate.id);
        return next;
      });
    }
  }

  if (!job) return <div className="muted">Loading…</div>;

  return (
    <div>
      <Link to="/jobs" className="muted" style={{ fontSize: 13 }}>
        ← All job descriptions
      </Link>
      <div className="page-title mt-16">{job.title}</div>
      <div className="page-subtitle">{job.candidate_count} candidates found so far</div>

      <div className="grid grid-2">
        <div className="card">
          <h3 style={{ marginTop: 0 }}>Search criteria</h3>
          <div className="field">
            <label>Keywords / skills (comma separated)</label>
            <input value={keywordsText} onChange={(e) => setKeywordsText(e.target.value)} />
          </div>
          <div className="field">
            <label>Locations (comma separated)</label>
            <input value={locationsText} onChange={(e) => setLocationsText(e.target.value)} />
          </div>
          <div className="field">
            <label>Seniority</label>
            <input value={seniority} onChange={(e) => setSeniority(e.target.value)} placeholder="e.g. Senior" />
          </div>
          <button className="btn secondary" onClick={saveCriteria} disabled={savingCriteria}>
            {savingCriteria ? "Saving…" : "Save criteria"}
          </button>
        </div>

        <div className="card">
          <h3 style={{ marginTop: 0 }}>Run a people search</h3>
          <div className="field">
            <label>Search source</label>
            <select value={provider} onChange={(e) => setProvider(e.target.value)}>
              {providers.map((p) => (
                <option key={p.id} value={p.id}>
                  {PROVIDER_LABELS[p.id] || p.id} {p.configured ? "" : "(demo mode)"}
                </option>
              ))}
            </select>
          </div>
          <p className="muted" style={{ fontSize: 13 }}>
            Uses the criteria above. Sources that aren't configured return realistic demo
            candidates so you can try the full flow end to end.
          </p>
          <button className="btn" onClick={runSearch} disabled={searching}>
            {searching ? "Searching…" : "Search candidates"}
          </button>
        </div>
      </div>

      {message && (
        <div className="card mt-16" style={messageIsError ? { borderColor: "var(--danger)", color: "var(--danger)" } : undefined}>
          {message}
        </div>
      )}

      <div className="mt-24 flex-between" style={{ flexWrap: "wrap", gap: 12 }}>
        <h3 style={{ margin: 0 }}>Candidates ({totalCandidates})</h3>
        <div className="flex gap-8" style={{ alignItems: "center" }}>
          <label className="muted" style={{ fontSize: 13, margin: 0 }}>
            Call with:
          </label>
          <select value={agentId} onChange={(e) => setAgentId(e.target.value)} style={{ width: 220 }}>
            <option value="">Select an agent…</option>
            {agents.map((a) => (
              <option key={a.id} value={a.id} disabled={!a.is_active}>
                {a.name}
                {a.is_active ? "" : " (inactive)"}
              </option>
            ))}
          </select>
        </div>
      </div>
      {agents.length === 0 && (
        <div className="muted mt-16" style={{ fontSize: 13 }}>
          No agents configured yet. <Link to="/agents">Create one</Link> before placing calls.
        </div>
      )}
      <div className="muted mt-16" style={{ fontSize: 13 }}>
        Tap <span aria-hidden>📞</span> next to a candidate to call them immediately — no scheduling window, one call
        at a time. Tap <span aria-hidden>🗓️</span> to schedule a call for a calling window instead. Both need a
        phone number on file first.
      </div>

      <div className="card mt-16">
        {candidates.length === 0 ? (
          <div className="muted">No candidates yet. Run a search above.</div>
        ) : (
          <>
            <table>
              <thead>
                <tr>
                  <th></th>
                  <th>Name</th>
                  <th>Title</th>
                  <th>Company</th>
                  <th>Location</th>
                  <th>Phone number</th>
                  <th>Source</th>
                  <th>Last call</th>
                </tr>
              </thead>
              <tbody>
                {candidates.map((c) => {
                  const hasPhone = !!c.phone_number;
                  const isCalling = callingIds.has(c.id);
                  
                  return (
                    <tr key={c.id} className="candidate-row">
                      <td>
                        <div className="flex gap-8">
                          <button
                            type="button"
                            className="call-icon-btn"
                            title={
                              !hasPhone
                                ? `Add a phone number for ${c.full_name} to enable calling`
                                : isCalling
                                ? "Calling…"
                                : `Call ${c.full_name} now`
                            }
                            aria-label={`Call ${c.full_name} now`}
                            onClick={() => callNow(c)}
                            disabled={isCalling || !hasPhone}
                          >
                            {isCalling ? (
                              <span className="call-icon-spinner" />
                            ) : !hasPhone ? (
                              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                <path
                                  d="M6.6 10.8c1.4 2.8 3.8 5.1 6.6 6.6l2.2-2.2c.3-.3.7-.4 1-.2 1.1.4 2.3.6 3.6.6.6 0 1 .4 1 1V20c0 .6-.4 1-1 1-9.4 0-17-7.6-17-17 0-.6.4-1 1-1h3.5c.6 0 1 .4 1 1 0 1.2.2 2.4.6 3.6.1.4 0 .8-.2 1L6.6 10.8z"
                                  fill="currentColor"
                                  opacity="0.5"
                                />
                                <line x1="3" y1="3" x2="21" y2="21" stroke="currentColor" strokeWidth="1.6" />
                              </svg>
                            ) : (
                              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                <path
                                  d="M6.6 10.8c1.4 2.8 3.8 5.1 6.6 6.6l2.2-2.2c.3-.3.7-.4 1-.2 1.1.4 2.3.6 3.6.6.6 0 1 .4 1 1V20c0 .6-.4 1-1 1-9.4 0-17-7.6-17-17 0-.6.4-1 1-1h3.5c.6 0 1 .4 1 1 0 1.2.2 2.4.6 3.6.1.4 0 .8-.2 1L6.6 10.8z"
                                  fill="currentColor"
                                />
                              </svg>
                            )}
                          </button>

                          <Link
                            to={hasPhone ? `/jobs/${jobId}/candidates/${c.id}/schedule` : "#"}
                            className="call-icon-btn schedule-icon-btn"
                            title={
                              !hasPhone
                                ? `Add a phone number for ${c.full_name} to enable scheduling`
                                : `Schedule a call for ${c.full_name}`
                            }
                            aria-label={`Schedule a call for ${c.full_name}`}
                            aria-disabled={!hasPhone}
                            onClick={(e) => {
                              if (!hasPhone) e.preventDefault();
                            }}
                          >
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                              <rect x="3" y="5" width="18" height="16" rx="2" stroke="currentColor" strokeWidth="1.6" />
                              <line x1="3" y1="9.5" x2="21" y2="9.5" stroke="currentColor" strokeWidth="1.6" />
                              <line x1="7" y1="2.5" x2="7" y2="6.5" stroke="currentColor" strokeWidth="1.6" />
                              <line x1="17" y1="2.5" x2="17" y2="6.5" stroke="currentColor" strokeWidth="1.6" />
                              <circle cx="12" cy="15" r="2.4" fill="currentColor" />
                            </svg>
                          </Link>
                        </div>
                      </td>
                      <td>
                        {c.linkedin_url ? (
                          <a href={c.linkedin_url} target="_blank" rel="noreferrer">
                            {c.full_name}
                          </a>
                        ) : (
                          c.full_name
                        )}
                      </td>
                      <td className="muted">{c.title || "—"}</td>
                      <td className="muted">{c.company || "—"}</td>
                      <td className="muted">{c.location || "—"}</td>
                      <td>
                        <PhoneEditor value={c.phone_number} onSave={(v) => updatePhone(c.id, v)} />
                      </td>
                      <td>
                        <span className="chip">{PROVIDER_LABELS[c.source_provider] || c.source_provider}</span>
                      </td>
                      <td>{c.latest_call_status ? <StatusBadge status={c.latest_call_status} /> : "—"}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>

            {totalPages > 1 && (
              <div className="flex-between mt-16">
                <button
                  className="btn secondary small"
                  onClick={() => loadCandidates(page - 1)}
                  disabled={page <= 1}
                >
                  Prev
                </button>
                <span className="muted" style={{ fontSize: 13 }}>
                  Page {page} of {totalPages}
                </span>
                <button
                  className="btn secondary small"
                  onClick={() => loadCandidates(page + 1)}
                  disabled={page >= totalPages}
                >
                  Next
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

function PhoneEditor({ value, onSave }: { value?: string | null; onSave: (v: string) => void }) {
  const [editing, setEditing] = useState(false);
  const [val, setVal] = useState(value || "");

  if (editing) {
    return (
      <div className="flex gap-8">
        <input
          value={val}
          onChange={(e) => setVal(e.target.value)}
          placeholder="+15551234567"
          style={{ width: 150 }}
        />
        <button
          className="btn small"
          onClick={() => {
            onSave(val);
            setEditing(false);
          }}
        >
          Save
        </button>
      </div>
    );
  }

  return (
    <span
      onClick={() => setEditing(true)}
      style={{ cursor: "pointer" }}
      className={value ? "" : "muted"}
      title="Click to edit (E.164 format, e.g. +15551234567)"
    >
      {value || "+ add phone"}
    </span>
  );
}
