import React from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const FAQS: { q: string; a: string }[] = [
  {
    q: "What does this app do?",
    a: "It helps you go from a job description to a set of candidates to contact, and then place outreach calls to them using a configurable voice agent.",
  },
  {
    q: "Where do candidates come from?",
    a: "Candidates are pulled from your configured search sources. If a source isn't configured with an API key, it returns realistic demo candidates so you can try the full flow end to end.",
  },
  {
    q: "Do I need to configure calling before I can use the app?",
    a: "You can explore job descriptions and candidate search without it. Placing an actual outreach call requires an active agent, which you can create on the Agents page.",
  },
  {
    q: "How do I see the status of a call?",
    a: "Open the Conversations page, or use the \"Refresh status\" button to pull the latest status for calls that are still in progress.",
  },
];

export default function FAQPage() {
  const { user } = useAuth();
  return (
    <div className="public-page">
      <header className="public-header">
        <Link to="/" className="brand">
          People<span>Reach</span>
        </Link>
        <nav className="public-nav">
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

      <main className="public-content">
        <div className="page-title">Frequently asked questions</div>
        <div className="card-list mt-16">
          {FAQS.map((item) => (
            <div className="card mt-16" key={item.q}>
              <h3 style={{ marginTop: 0 }}>{item.q}</h3>
              <p className="muted" style={{ marginBottom: 0 }}>
                {item.a}
              </p>
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}
