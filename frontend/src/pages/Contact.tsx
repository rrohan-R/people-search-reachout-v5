import React, { useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function ContactPage() {
  const { user } = useAuth();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [submitted, setSubmitted] = useState(false);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    // No backend endpoint for contact submissions yet; just acknowledge locally.
    setSubmitted(true);
  }

  return (
    <div className="public-page">
      <header className="public-header">
        <Link to="/" className="brand">
          People<span>Reach</span>
        </Link>
        <nav className="public-nav">
          <Link to="/faq">FAQ</Link>
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
        <div className="page-title">Contact us</div>
        <div className="page-subtitle">Questions, feedback, or need help? Send us a message.</div>

        <div className="card" style={{ maxWidth: 480 }}>
          {submitted ? (
            <div>Thanks for reaching out — we'll get back to you shortly.</div>
          ) : (
            <form onSubmit={handleSubmit}>
              <div className="field">
                <label>Name</label>
                <input value={name} onChange={(e) => setName(e.target.value)} required />
              </div>
              <div className="field">
                <label>Email</label>
                <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
              </div>
              <div className="field">
                <label>Message</label>
                <textarea
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  rows={5}
                  required
                />
              </div>
              <button className="btn" type="submit">
                Send message
              </button>
            </form>
          )}
        </div>
      </main>
    </div>
  );
}
