import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import * as api from "../api/endpoints";
import { OutreachCall } from "../types";
import StatusBadge from "../components/StatusBadge";

function humanizeKey(key: string) {
  return key
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatValue(value: any): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

export default function CallDetailPage() {
  const { callId } = useParams<{ callId: string }>();
  const [call, setCall] = useState<OutreachCall | null>(null);
  const [loading, setLoading] = useState(true);

  async function load() {
    if (!callId) return;
    setLoading(true);
    const data = await api.getCallDetail(callId);
    setCall(data);
    setLoading(false);
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [callId]);


  if (loading || !call) return <div className="muted">Loading…</div>;

  const rawResult = call.result || {};
  const { error: callError, details: callErrorDetails, info: callInfo, ...conversationResult } = rawResult as {
    error?: string;
    details?: any[];
    info?: string;
    [key: string]: any;
  };
  const resultEntries = Object.entries(conversationResult);

  return (
    <div>
      <Link to="/calls" className="muted" style={{ fontSize: 13 }}>
        ← All conversations
      </Link>

      <div className="flex-between mt-16">
        <div>
          <div className="page-title">{call.candidate_name}</div>
          <div className="page-subtitle">
            {call.candidate_title} {call.candidate_company ? `at ${call.candidate_company}` : ""} ·{" "}
            {call.job_description_title}
          </div>
        </div>
        <div className="flex gap-8" style={{ alignItems: "center" }}>
          <StatusBadge status={call.status} />
          {call.job_description_id && (
            <Link
              to={`/jobs/${call.job_description_id}/candidates/${call.candidate_id}/schedule`}
              className="btn secondary small"
            >
              Schedule again
            </Link>
          )}
        </div>
      </div>

      {call.guardrails && (
        <div className="card mt-16">
          <div style={{ fontWeight: 700, marginBottom: 4 }}>Placed from a schedule</div>
          <div className="muted">
            Calling window: {(call.guardrails.allowed_days || []).join("/")} · {call.guardrails.earliest_call_time}–
            {call.guardrails.last_call_time} ({call.timezone})
          </div>
        </div>
      )}

      {callError && (
        <div className="card mt-16" style={{ borderColor: "var(--danger)" }}>
          <div style={{ fontWeight: 700, color: "var(--danger)", marginBottom: 4 }}>
            Call failed to place
          </div>
          <div style={{ color: "var(--danger)" }}>{callError}</div>
          {Array.isArray(callErrorDetails) && callErrorDetails.length > 0 && (
            <ul style={{ margin: "8px 0 0", paddingLeft: 18, color: "var(--danger)", fontSize: 13 }}>
              {callErrorDetails.map((d, i) => (
                <li key={i}>{typeof d === "string" ? d : JSON.stringify(d)}</li>
              ))}
            </ul>
          )}
          <div className="muted mt-16" style={{ fontSize: 12 }}>
            Full request/response details are in the backend logs — search for this call's Request ID below.
          </div>
        </div>
      )}
      {callInfo && !callError && (
        <div className="card mt-16">{callInfo}</div>
      )}

      <div className="grid grid-3 mt-16">
        <div className="stat-card">
          <div className="stat-value">
            {call.duration_seconds ? `${Math.round((call.duration_seconds / 60) * 10) / 10}m` : "—"}
          </div>
          <div className="stat-label">Call duration</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{call.engagement_status || "—"}</div>
          <div className="stat-label">Engagement</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{call.answered_by || "—"}</div>
          <div className="stat-label">Answered by</div>
        </div>
      </div>

      <div className="grid grid-2 mt-24">
        <div className="card">
          <h3 style={{ marginTop: 0 }}>Conversation results</h3>
          {resultEntries.length === 0 ? (
            <div className="muted">
              No structured results yet. Results appear here once the call completes — use the
              "Refresh status" button on the Conversations page to pull the latest results.
            </div>
          ) : (
            resultEntries.map(([key, value]) => (
              <div className="qa-item" key={key}>
                <div className="qa-key">{humanizeKey(key)}</div>
                <div className="qa-value">{formatValue(value)}</div>
              </div>
            ))
          )}
        </div>

        <div className="card">
          <h3 style={{ marginTop: 0 }}>Call details</h3>
          <div className="qa-item">
            <div className="qa-key">Phone number</div>
            <div className="qa-value">{call.mobile_number}</div>
          </div>
          <div className="qa-item">
            <div className="qa-key">Triggered by</div>
            <div className="qa-value">{call.triggered_by || "—"}</div>
          </div>
          <div className="qa-item">
            <div className="qa-key">Reference ID</div>
            <div className="qa-value">{call.provider_call_id || "—"}</div>
          </div>
          <div className="qa-item">
            <div className="qa-key">Request ID</div>
            <div className="qa-value">{call.request_id || "—"}</div>
          </div>
          <div className="qa-item">
            <div className="qa-key">Created</div>
            <div className="qa-value">{new Date(call.created_at).toLocaleString()}</div>
          </div>
          {call.recording_url && (
            <div className="qa-item">
              <div className="qa-key">Recording</div>
              <audio controls src={call.recording_url} style={{ width: "100%", marginTop: 6 }} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
