import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import * as api from "../api/endpoints";
import { CallSchedule, OutreachCall } from "../types";
import StatusBadge from "../components/StatusBadge";

function ScheduleStatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    PENDING: "scheduled",
    DISPATCHED: "in_progress",
    CANCELLED: "cancelled",
    FAILED: "failed",
  };
  return <span className={`badge ${map[status] || "not_started"}`}>{status}</span>;
}

function windowLabel(s: CallSchedule) {
  return `${s.allowed_days.join("/")} · ${s.earliest_call_time}–${s.last_call_time} (${s.timezone})`;
}

export default function SchedulesPage() {
  const [schedules, setSchedules] = useState<CallSchedule[]>([]);
  const [calls, setCalls] = useState<OutreachCall[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [messageIsError, setMessageIsError] = useState(false);

  async function load() {
    setLoading(true);
    const [s, c] = await Promise.all([api.listSchedules(), api.listAllCalls()]);
    setSchedules(s);
    setCalls(c);
    setLoading(false);
  }

  useEffect(() => {
    load();
  }, []);

  async function handleDelete(schedule: CallSchedule) {
    const isPending = schedule.status === "PENDING";
    const confirmMsg = isPending
      ? `Delete this pending schedule for ${schedule.candidate_name}? It will never be dialed.`
      : `Remove this schedule record for ${schedule.candidate_name}? (The call itself, if any, stays on the Conversations page.)`;
    if (!window.confirm(confirmMsg)) return;
    setBusyId(schedule.id);
    try {
      await api.deleteSchedule(schedule.id);
      setSchedules((prev) => prev.filter((s) => s.id !== schedule.id));
    } catch (err: any) {
      setMessageIsError(true);
      setMessage(err?.response?.data?.detail || "Could not delete this schedule.");
    } finally {
      setBusyId(null);
    }
  }

  async function handleCallNow(schedule: CallSchedule) {
    setBusyId(schedule.id);
    setMessage(null);
    try {
      const updated = await api.dispatchScheduleNow(schedule.id);
      setSchedules((prev) => prev.map((s) => (s.id === schedule.id ? updated : s)));
      setMessageIsError(false);
      setMessage(`Calling ${schedule.candidate_name} now — see Conversations for live status.`);
    } catch (err: any) {
      setMessageIsError(true);
      setMessage(err?.response?.data?.detail || "Could not place this call.");
    } finally {
      setBusyId(null);
    }
  }

  const pending = schedules.filter((s) => s.status === "PENDING");
  const past = schedules.filter((s) => s.status !== "PENDING");

  return (
    <div>
      <div className="page-title">Schedules</div>
      <div className="page-subtitle">
        Calls waiting for their calling window, plus anything already sent or cancelled. Pending schedules can be
        edited or deleted any time before their window opens — nothing is sent to Hunar until then.
      </div>

      {message && (
        <div className="card mt-16" style={messageIsError ? { borderColor: "var(--danger)", color: "var(--danger)" } : undefined}>
          {message}
        </div>
      )}

      <div className="section-label">Pending ({pending.length})</div>
      <div className="card">
        {loading ? (
          <div className="muted">Loading…</div>
        ) : pending.length === 0 ? (
          <div className="muted">
            Nothing scheduled right now. Open a job's candidate list and tap the schedule icon next to a candidate.
          </div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Candidate</th>
                <th>Job</th>
                <th>Agent</th>
                <th>Window</th>
                <th>Notes</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {pending.map((s) => (
                <tr key={s.id}>
                  <td>
                    <div>{s.candidate_name}</div>
                    <div className="muted" style={{ fontSize: 12 }}>{s.candidate_phone}</div>
                  </td>
                  <td className="muted">{s.job_description_title || "—"}</td>
                  <td className="muted">{s.agent_name || "—"}</td>
                  <td className="muted">{windowLabel(s)}</td>
                  <td className="muted">{s.notes || "—"}</td>
                  <td>
                    <div className="flex gap-8">
                      <Link to={`/schedules/${s.id}/edit`} className="btn secondary small">
                        Update
                      </Link>
                      <button
                        className="btn small"
                        disabled={busyId === s.id}
                        onClick={() => handleCallNow(s)}
                      >
                        Call now
                      </button>
                      <button
                        className="btn danger small"
                        disabled={busyId === s.id}
                        onClick={() => handleDelete(s)}
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="section-label">Dispatched, cancelled &amp; failed schedules ({past.length})</div>
      <div className="card">
        {past.length === 0 ? (
          <div className="muted">Nothing here yet.</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Candidate</th>
                <th>Window</th>
                <th>Schedule status</th>
                <th>Call status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {past.map((s) => (
                <tr key={s.id}>
                  <td>
                    <div>{s.candidate_name}</div>
                    <div className="muted" style={{ fontSize: 12 }}>{s.job_description_title}</div>
                  </td>
                  <td className="muted">{windowLabel(s)}</td>
                  <td>
                    <ScheduleStatusBadge status={s.status} />
                    {s.failure_reason && (
                      <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>{s.failure_reason}</div>
                    )}
                  </td>
                  <td>{s.outreach_call_status ? <StatusBadge status={s.outreach_call_status} /> : "—"}</td>
                  <td>
                    <div className="flex gap-8">
                      {s.outreach_call_id && <Link to={`/calls/${s.outreach_call_id}`}>View call</Link>}
                      <button className="btn secondary small" disabled={busyId === s.id} onClick={() => handleDelete(s)}>
                        Remove
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="section-label">Conversations you can schedule again</div>
      <div className="card">
        {calls.length === 0 ? (
          <div className="muted">No calls placed yet.</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Candidate</th>
                <th>Job</th>
                <th>Status</th>
                <th>When</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {calls.slice(0, 25).map((c) => (
                <tr key={c.id}>
                  <td>
                    <div>{c.candidate_name}</div>
                    <div className="muted" style={{ fontSize: 12 }}>{c.candidate_title}</div>
                  </td>
                  <td className="muted">{c.job_description_title}</td>
                  <td>
                    <StatusBadge status={c.status} />
                  </td>
                  <td className="muted">{new Date(c.created_at).toLocaleString()}</td>
                  <td>
                    {c.job_description_id ? (
                      <Link to={`/jobs/${c.job_description_id}/candidates/${c.candidate_id}/schedule`}>
                        Schedule again
                      </Link>
                    ) : (
                      <Link to={`/calls/${c.id}`}>View</Link>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
