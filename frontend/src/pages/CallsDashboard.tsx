import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import * as api from "../api/endpoints";
import { OutreachCall } from "../types";
import StatusBadge from "../components/StatusBadge";
import ResultPreview from "../components/ResultPreview";

const STATUS_FILTERS = [
  "",
  "NOT_STARTED",
  "SCHEDULED",
  "INITIATED",
  "RINGING",
  "IN_PROGRESS",
  "COMPLETED",
  "NOT_CONNECTED",
  "CANCELLED",
  "FAILED",
];

export default function CallsPage() {
  const [calls, setCalls] = useState<OutreachCall[]>([]);
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);

  async function load() {
    setLoading(true);
    const data = await api.listAllCalls(status || undefined);
    setCalls(data);
    setLoading(false);
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status]);

  async function handleSync() {
    setSyncing(true);
    try {
      await api.syncCalls();
      await load();
    } catch {
      // ignore - likely calling isn't configured yet
    } finally {
      setSyncing(false);
    }
  }

  return (
    <div>
      <div className="flex-between">
        <div>
          <div className="page-title">Conversations</div>
          <div className="page-subtitle">All outreach calls you've placed.</div>
        </div>
        <button className="btn secondary" onClick={handleSync} disabled={syncing}>
          {syncing ? "Refreshing…" : "Refresh status"}
        </button>
      </div>

      <div className="field" style={{ maxWidth: 260 }}>
        <label>Filter by status</label>
        <select value={status} onChange={(e) => setStatus(e.target.value)}>
          {STATUS_FILTERS.map((s) => (
            <option key={s} value={s}>
              {s || "All statuses"}
            </option>
          ))}
        </select>
      </div>

      <div className="card mt-16">
        {loading ? (
          <div className="muted">Loading…</div>
        ) : calls.length === 0 ? (
          <div className="muted">No calls yet.</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Candidate</th>
                <th>Job</th>
                <th>Phone</th>
                <th>Status</th>
                <th>Response</th>
                <th>Duration</th>
                <th>Triggered by</th>
                <th>When</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {calls.map((c) => (
                <tr key={c.id}>
                  <td>
                    <div>{c.candidate_name}</div>
                    <div className="muted" style={{ fontSize: 12 }}>
                      {c.candidate_title}
                    </div>
                  </td>
                  <td className="muted">{c.job_description_title}</td>
                  <td className="muted">{c.mobile_number}</td>
                  <td>
                    <StatusBadge status={c.status} />
                  </td>
                  <td>
                    <Link to={`/calls/${c.id}`}>
                      <ResultPreview result={c.result} />
                    </Link>
                  </td>
                  <td className="muted">
                    {c.duration_seconds ? `${Math.round((c.duration_seconds / 60) * 10) / 10} min` : "—"}
                  </td>
                  <td className="muted">{c.triggered_by || "—"}</td>
                  <td className="muted">{new Date(c.created_at).toLocaleString()}</td>
                  <td>
                    <Link to={`/calls/${c.id}`}>View</Link>
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
