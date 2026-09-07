import React from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function HomePage() {
  const { user } = useAuth();

  return (
    <div className="public-page">
      <header className="public-header">
        <div className="brand">
          People<span>Reach</span>
        </div>
        <nav className="public-nav">
          <Link to="/faq">FAQ</Link>
          <Link to="/contact">Contact Us</Link>
          {user ? (
            <Link to="/dashboard" className="btn small">
              Go to dashboard
            </Link>
          ) : (
            <Link to="/login" className="btn small">
              Sign in
            </Link>
          )}
        </nav>
      </header>

      <main className="public-hero">
        <div className="page-title" style={{ fontSize: 32 }}>
          Find candidates. Reach out. Without the busywork.
        </div>
        <div className="page-subtitle" style={{ fontSize: 16, maxWidth: 560 }}>
          Paste a job description, search for matching candidates, and let a voice agent
          make the first call — all from one dashboard.
        </div>
        <div className="mt-24 flex gap-8">
          {user ? (
            <Link to="/dashboard" className="btn">
              Go to dashboard
            </Link>
          ) : (
            <Link to="/login" className="btn">
              Get started
            </Link>
          )}
          <Link to="/faq" className="btn secondary">
            Learn more
          </Link>
        </div>

        <div className="grid grid-3 mt-24" style={{ width: "100%", maxWidth: 900 }}>
          <div className="card">
            <h3 style={{ marginTop: 0 }}>1. Paste a job description</h3>
            <p className="muted" style={{ fontSize: 14 }}>
              We automatically extract keywords, seniority, and locations to search on.
            </p>
          </div>
          <div className="card">
            <h3 style={{ marginTop: 0 }}>2. Search candidates</h3>
            <p className="muted" style={{ fontSize: 14 }}>
              Pull matching candidates from your configured search sources.
            </p>
          </div>
          <div className="card">
            <h3 style={{ marginTop: 0 }}>3. Call automatically</h3>
            <p className="muted" style={{ fontSize: 14 }}>
              Configure a voice agent and place outreach calls directly from your dashboard.
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}
