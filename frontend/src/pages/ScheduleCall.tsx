import React, { useEffect, useState } from "react";
import { useParams, useNavigate, useSearchParams, Link } from "react-router-dom";
import * as api from "../api/endpoints";
import { Agent, Candidate, CallSchedule } from "../types";
import {
  WEEKDAY_OPTIONS,
  TIMEZONE_OPTIONS,
  DEFAULT_WEEKDAYS,
  DEFAULT_EARLIEST_TIME,
  DEFAULT_LAST_TIME,
  DEFAULT_TIMEZONE,
} from "../constants/scheduleOptions";

export default function ScheduleCallPage() {
  // Create mode: /jobs/:jobId/candidates/:candidateId/schedule
  // Edit mode:   /schedules/:scheduleId/edit
  const { jobId, candidateId, scheduleId } = useParams<{
    jobId?: string;
    candidateId?: string;
    scheduleId?: string;
  }>();
  const isEdit = !!scheduleId;
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [candidate, setCandidate] = useState<Candidate | null>(null);
  const [existingSchedule, setExistingSchedule] = useState<CallSchedule | null>(null);
  const [effectiveJobId, setEffectiveJobId] = useState<string | undefined>(jobId);
  const [agents, setAgents] = useState<Agent[]>([]);

  const [agentId, setAgentId] = useState(searchParams.get("agentId") || "");
  const [days, setDays] = useState<string[]>(DEFAULT_WEEKDAYS);
  const [earliest, setEarliest] = useState(DEFAULT_EARLIEST_TIME);
  const [last, setLast] = useState(DEFAULT_LAST_TIME);
  const [timezone, setTimezone] = useState(DEFAULT_TIMEZONE);
  const [notes, setNotes] = useState("");

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const agentList = await api.listAgents();
        setAgents(agentList);

        if (isEdit && scheduleId) {
          const sched = await api.getSchedule(scheduleId);
          setExistingSchedule(sched);
          setEffectiveJobId(sched.job_description_id || undefined);
          setAgentId(sched.agent_id);
          setDays(sched.allowed_days);
          setEarliest(sched.earliest_call_time);
          setLast(sched.last_call_time);
          setTimezone(sched.timezone);
          setNotes(sched.notes || "");
          if (sched.job_description_id) {
            const c = await api.getCandidate(sched.job_description_id, sched.candidate_id);
            setCandidate(c);
          }
        } else if (jobId && candidateId) {
          const c = await api.getCandidate(jobId, candidateId);
          setCandidate(c);
          if (!agentId) {
            const active = agentList.filter((a) => a.is_active);
            setAgentId(active[0]?.id || "");
          }
        }
      } catch (err: any) {
        setError(err?.response?.data?.detail || "Failed to load scheduling details.");
      } finally {
        setLoading(false);
      }
    }
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scheduleId, jobId, candidateId]);

  function toggleDay(day: string) {
    setDays((prev) => (prev.includes(day) ? prev.filter((d) => d !== day) : [...prev, day]));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!agentId) {
      setError("Select an agent for this schedule.");
      return;
    }
    if (days.length < 3) {
      setError("Pick at least 3 calling days.");
      return;
    }
    if (earliest >= last) {
      setError("The start time must be before the end time.");
      return;
    }
    setSaving(true);
    try {
      if (isEdit && scheduleId) {
        await api.updateSchedule(scheduleId, {
          agent_id: agentId,
          allowed_days: days,
          earliest_call_time: earliest,
          last_call_time: last,
          timezone,
          notes: notes || undefined,
        });
      } else if (candidate) {
        await api.createSchedule({
          candidate_id: candidate.id,
          agent_id: agentId,
          allowed_days: days,
          earliest_call_time: earliest,
          last_call_time: last,
          timezone,
          notes: notes || undefined,
        });
      }
      navigate("/schedules");
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Could not save this schedule.");
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <div className="muted">Loading…</div>;

  if (isEdit && existingSchedule && existingSchedule.status !== "PENDING") {
    return (
      <div>
        <Link to="/schedules" className="muted" style={{ fontSize: 13 }}>
          ← All schedules
        </Link>
        <div className="card mt-16">
          This schedule is <strong>{existingSchedule.status}</strong> and can no longer be edited.
          {existingSchedule.outreach_call_id && (
            <>
              {" "}
              <Link to={`/calls/${existingSchedule.outreach_call_id}`}>View the call</Link>.
            </>
          )}
        </div>
      </div>
    );
  }

  return (
    <div>
      <Link to={isEdit ? "/schedules" : `/jobs/${effectiveJobId || jobId}`} className="muted" style={{ fontSize: 13 }}>
        ← {isEdit ? "All schedules" : "Back to candidates"}
      </Link>
      <div className="page-title mt-16">{isEdit ? "Update schedule" : "Schedule a call"}</div>
      <div className="page-subtitle">
        {candidate ? (
          <>
            For <strong>{candidate.full_name}</strong>
            {candidate.title ? ` · ${candidate.title}` : ""}
            {candidate.company ? ` at ${candidate.company}` : ""} · {candidate.phone_number || "no phone on file"}
          </>
        ) : (
          "Pick the days and time window this call is allowed to ring in."
        )}
      </div>

      <form onSubmit={handleSubmit} className="card" style={{ maxWidth: 560 }}>
        <div className="field">
          <label>Call with agent</label>
          <select value={agentId} onChange={(e) => setAgentId(e.target.value)}>
            <option value="">Select an agent…</option>
            {agents.map((a) => (
              <option key={a.id} value={a.id} disabled={!a.is_active}>
                {a.name}
                {a.is_active ? "" : " (inactive)"}
              </option>
            ))}
          </select>
        </div>

        <div className="field">
          <label>Calling days (pick at least 3)</label>
          <div className="flex gap-8" style={{ flexWrap: "wrap" }}>
            {WEEKDAY_OPTIONS.map((d) => (
              <button
                type="button"
                key={d.value}
                className={`btn small ${days.includes(d.value) ? "" : "secondary"}`}
                onClick={() => toggleDay(d.value)}
              >
                {d.label}
              </button>
            ))}
          </div>
        </div>

        <div className="grid grid-2">
          <div className="field">
            <label>Earliest call time</label>
            <input type="time" value={earliest} onChange={(e) => setEarliest(e.target.value)} />
          </div>
          <div className="field">
            <label>Latest call time</label>
            <input type="time" value={last} onChange={(e) => setLast(e.target.value)} />
          </div>
        </div>
        <p className="muted" style={{ fontSize: 12, marginTop: -8 }}>
          The window must span at least 3 hours. The call is placed as soon as this window opens (checked every
          minute) — or right away if the window is already open when you save.
        </p>

        <div className="field">
          <label>Timezone</label>
          <select value={timezone} onChange={(e) => setTimezone(e.target.value)}>
            {TIMEZONE_OPTIONS.map((tz) => (
              <option key={tz} value={tz}>
                {tz}
              </option>
            ))}
          </select>
        </div>

        <div className="field">
          <label>Notes (optional, just for your own reference)</label>
          <input value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="e.g. Follow-up after first attempt" />
        </div>

        {error && <div className="error-text">{error}</div>}

        <div className="flex gap-8 mt-16">
          <button className="btn" type="submit" disabled={saving}>
            {saving ? "Saving…" : isEdit ? "Save changes" : "Save schedule"}
          </button>
          <button
            type="button"
            className="btn secondary"
            onClick={() => navigate(isEdit ? "/schedules" : `/jobs/${effectiveJobId || jobId}`)}
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}
