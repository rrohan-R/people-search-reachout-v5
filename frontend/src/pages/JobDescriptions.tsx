import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import * as api from "../api/endpoints";
import { JobDescription } from "../types";

export default function JobsPage() {
  const [jobs, setJobs] = useState<JobDescription[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [title, setTitle] = useState("");
  const [rawText, setRawText] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  async function load() {
    setLoading(true);
    const data = await api.listJobs();
    setJobs(data);
    setLoading(false);
  }

  useEffect(() => {
    load();
  }, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const job = await api.createJob({ title, raw_text: rawText });
      navigate(`/jobs/${job.id}`);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Failed to create job description");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(id: string) {
    if (!confirm("Delete this job description and all its candidates/calls?")) return;
    await api.deleteJob(id);
    load();
  }

  return (
    <div>
      <div className="flex-between">
        <div>
          <div className="page-title">Job Descriptions</div>
          <div className="page-subtitle">Paste a JD, then search for and reach out to matching candidates.</div>
        </div>
        <button className="btn" onClick={() => setShowForm((v) => !v)}>
          {showForm ? "Cancel" : "+ New job description"}
        </button>
      </div>

      {showForm && (
        <form className="card mt-16" onSubmit={handleCreate}>
          <div className="field">
            <label>Job title</label>
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Senior Backend Engineer"
              required
            />
          </div>
          <div className="field">
            <label>Job description</label>
            <textarea
              value={rawText}
              onChange={(e) => setRawText(e.target.value)}
              rows={10}
              placeholder="Paste the full job description here…"
              required
            />
          </div>
          {error && <div className="error-text">{error}</div>}
          <button className="btn" type="submit" disabled={submitting}>
            {submitting ? "Creating…" : "Create & extract search criteria"}
          </button>
        </form>
      )}

      <div className="mt-24">
        {loading ? (
          <div className="muted">Loading…</div>
        ) : jobs.length === 0 ? (
          <div className="card muted">No job descriptions yet. Create one to get started.</div>
        ) : (
          <div className="grid grid-2">
            {jobs.map((job) => (
              <div className="card" key={job.id}>
                <div className="flex-between">
                  <Link to={`/jobs/${job.id}`} style={{ fontWeight: 700, fontSize: 16 }}>
                    {job.title}
                  </Link>
                  <button className="btn danger small" onClick={() => handleDelete(job.id)}>
                    Delete
                  </button>
                </div>
                <div className="muted mt-16" style={{ fontSize: 13 }}>
                  {job.candidate_count} candidate{job.candidate_count === 1 ? "" : "s"} found
                </div>
                <div className="mt-16">
                  {job.keywords.slice(0, 6).map((k) => (
                    <span key={k} className="chip">
                      {k}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
