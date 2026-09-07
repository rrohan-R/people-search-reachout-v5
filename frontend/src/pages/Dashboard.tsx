import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import * as api from "../api/endpoints";
import { Agent, Candidate, JobOverview } from "../types";
import StatusBadge from "../components/StatusBadge";
import ResultPreview from "../components/ResultPreview";

interface Summary {
  job_count: number;
  candidate_count: number;
  call_count: number;
  status_counts: Record<string, number>;
}

export default function DashboardPage() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [overview, setOverview] = useState<JobOverview[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    const [s, jobsOverview, agentList] = await Promise.all([
      api.getSummary(),
      api.getJobsOverview(),
      api.listAgents(),
    ]);
    setSummary(s);
    setOverview(jobsOverview);
    setAgents(agentList);
    setLoading(false);
  }

  useEffect(() => {
    load();
  }, []);

  function patchJobCalls(jobId: string, updater: (job: JobOverview) => JobOverview) {
    setOverview((prev) => prev.map((j) => (j.job_id === jobId ? updater(j) : j)));
  }

  return (
    <div>
      <div className="page-title">Dashboard</div>
      <div className="page-subtitle">Overview of your job searches, candidates, and outreach calls.</div>

      {loading || !summary ? (
        <div className="muted">Loading…</div>
      ) : (
        <>
          <div className="grid grid-3">
            <div className="stat-card">
              <div className="stat-value">{summary.job_count}</div>
              <div className="stat-label">Job descriptions</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{summary.candidate_count}</div>
              <div className="stat-label">Candidates found</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{summary.call_count}</div>
              <div className="stat-label">Outreach calls placed</div>
            </div>
          </div>

          <div className="mt-24 flex gap-8" style={{ flexWrap: "wrap" }}>
            {Object.entries(summary.status_counts).map(([status, count]) => (
              <div key={status} className="chip">
                <StatusBadge status={status} /> &nbsp;{count}
              </div>
            ))}
          </div>

          <div className="mt-24 flex-between">
            <h3 style={{ margin: 0 }}>Jobs &amp; candidates</h3>
            <Link to="/jobs" className="btn secondary small">
              Manage job descriptions
            </Link>
          </div>

          {overview.length === 0 ? (
            <div className="card mt-16 muted">
              No job descriptions yet. <Link to="/jobs">Create one</Link> to get started.
            </div>
          ) : (
            overview.map((job) => (
              <JobOverviewCard
                key={job.job_id}
                job={job}
                agents={agents}
                onCallsChange={(updater) => patchJobCalls(job.job_id, updater)}
              />
            ))
          )}
        </>
      )}
    </div>
  );
}

function JobOverviewCard({
  job,
  agents,
  onCallsChange,
}: {
  job: JobOverview;
  agents: Agent[];
  onCallsChange: (updater: (job: JobOverview) => JobOverview) => void;
}) {
  const [showMore, setShowMore] = useState(false);
  const [otherCandidates, setOtherCandidates] = useState<Candidate[] | null>(null);
  const [loadingOthers, setLoadingOthers] = useState(false);

  const calledCandidateIds = new Set(job.calls.map((c) => c.candidate_id));

  async function loadOtherCandidates() {
    setLoadingOthers(true);
    try {
      const result = await api.listCandidates(job.job_id, 1, 100);
      setOtherCandidates(result.items.filter((c) => !calledCandidateIds.has(c.id)));
    } finally {
      setLoadingOthers(false);
    }
  }

  function toggleShowMore() {
    const next = !showMore;
    setShowMore(next);
    if (next && otherCandidates === null) {
      loadOtherCandidates();
    }
  }

  async function placeCall(candidateId: string, agentId: string) {
    const calls = await api.launchOutreach(job.job_id, { candidate_ids: [candidateId], agent_id: agentId });
    if (calls.length > 0) {
      onCallsChange((j) => ({ ...j, calls: [calls[0], ...j.calls] }));
      setOtherCandidates((prev) => (prev ? prev.filter((c) => c.id !== candidateId) : prev));
    }
    return calls;
  }

  return (
    <div className="card mt-16">
      <div className="flex-between">
        <div>
          <Link to={`/jobs/${job.job_id}`} style={{ fontWeight: 700, fontSize: 15 }}>
            {job.title}
          </Link>
          <div className="muted" style={{ fontSize: 13 }}>
            {job.candidate_count} candidate{job.candidate_count === 1 ? "" : "s"} found ·{" "}
            {job.calls.length} contacted
          </div>
        </div>
      </div>

      {job.calls.length === 0 ? (
        <div className="muted mt-16" style={{ fontSize: 13 }}>
          No candidates contacted yet for this job.
        </div>
      ) : (
        <table className="mt-16">
          <thead>
            <tr>
              <th>Candidate</th>
              <th>Status</th>
              <th>Response</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {job.calls.map((c) => (
              <CallRow
                key={c.id}
                name={c.candidate_name || "—"}
                status={c.status}
                statusLink={`/calls/${c.id}`}
                result={c.result}
              >
                <CallAction agents={agents} onCall={(agentId) => placeCall(c.candidate_id, agentId)} label="Call again" />
              </CallRow>
            ))}
          </tbody>
        </table>
      )}

      <div className="mt-16">
        <button className="btn secondary small" onClick={toggleShowMore}>
          {showMore ? "Hide other candidates" : "Show other candidates to call"}
        </button>
      </div>

      {showMore && (
        <div className="mt-16">
          {loadingOthers ? (
            <div className="muted">Loading…</div>
          ) : !otherCandidates || otherCandidates.length === 0 ? (
            <div className="muted" style={{ fontSize: 13 }}>
              No other candidates available to call.
            </div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Candidate</th>
                  <th>Phone</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {otherCandidates.map((c) => (
                  <CallRow key={c.id} name={c.full_name} extra={c.phone_number || "no phone on file"}>
                    <CallAction
                      agents={agents}
                      disabled={!c.phone_number}
                      onCall={(agentId) => placeCall(c.id, agentId)}
                      label="Call"
                    />
                  </CallRow>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}

function CallRow({
  name,
  status,
  statusLink,
  extra,
  result,
  children,
}: {
  name: string;
  status?: string;
  statusLink?: string;
  extra?: string;
  result?: Record<string, any>;
  children: React.ReactNode;
}) {
  return (
    <tr>
      <td>{name}</td>
      <td className={status ? "" : "muted"}>
        {status ? (
          statusLink ? (
            <Link to={statusLink}>
              <StatusBadge status={status} />
            </Link>
          ) : (
            <StatusBadge status={status} />
          )
        ) : (
          extra
        )}
      </td>
      {status && (
        <td>
          {statusLink ? (
            <Link to={statusLink}>
              <ResultPreview result={result} />
            </Link>
          ) : (
            <ResultPreview result={result} />
          )}
        </td>
      )}
      <td>{children}</td>
    </tr>
  );
}

function CallAction({
  agents,
  onCall,
  label,
  disabled,
}: {
  agents: Agent[];
  onCall: (agentId: string) => Promise<any>;
  label: string;
  disabled?: boolean;
}) {
  const activeAgents = agents.filter((a) => a.is_active);
  const [agentId, setAgentId] = useState(activeAgents[0]?.id || "");
  const [calling, setCalling] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleClick() {
    if (!agentId) {
      setError("Select an agent");
      return;
    }
    setCalling(true);
    setError(null);
    try {
      await onCall(agentId);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Call failed");
    } finally {
      setCalling(false);
    }
  }

  if (activeAgents.length === 0) {
    return (
      <span className="muted" style={{ fontSize: 12 }}>
        <Link to="/agents">Configure an agent</Link>
      </span>
    );
  }

  return (
    <div className="flex gap-8" style={{ alignItems: "center" }}>
      <select value={agentId} onChange={(e) => setAgentId(e.target.value)} style={{ width: 150 }}>
        {activeAgents.map((a) => (
          <option key={a.id} value={a.id}>
            {a.name}
          </option>
        ))}
      </select>
      <button className="btn small" onClick={handleClick} disabled={calling || disabled}>
        {calling ? "Calling…" : label}
      </button>
      {error && <span className="error-text">{error}</span>}
    </div>
  );
}
