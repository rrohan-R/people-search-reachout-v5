import React, { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function LoginPage() {
  const { user, login, register, loading, error } = useAuth();
  const navigate = useNavigate();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");

  if (user) return <Navigate to="/dashboard" replace />;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    try {
      if (mode === "login") {
        await login(username, password);
      } else {
        await register(username, password, fullName);
      }
      navigate("/dashboard");
    } catch {
      // error is surfaced via context state
    }
  }

  return (
    <div className="login-wrap">
      <div className="login-card">
        <div className="page-title">Reachout</div>
        <div className="page-subtitle">
          {mode === "login" ? "Sign in to your account" : "Create a new account"}
        </div>

        <form onSubmit={handleSubmit}>
          {mode === "register" && (
            <div className="field">
              <label>Full name</label>
              <input value={fullName} onChange={(e) => setFullName(e.target.value)} placeholder="Jane Doe" />
            </div>
          )}
          <div className="field">
            <label>Username</label>
            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="admin"
              autoFocus
              required
            />
          </div>
          <div className="field">
            <label>Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
            />
          </div>

          {error && <div className="error-text">{error}</div>}

          <button className="btn" type="submit" style={{ width: "100%", marginTop: 8 }} disabled={loading}>
            {loading ? "Please wait…" : mode === "login" ? "Sign in" : "Create account"}
          </button>
        </form>

        <div className="mt-16 muted" style={{ fontSize: 13, textAlign: "center" }}>
          {mode === "login" ? (
            <>
              Don&apos;t have an account?{" "}
              <a href="#" onClick={(e) => { e.preventDefault(); setMode("register"); }}>
                Register
              </a>
            </>
          ) : (
            <>
              Already have an account?{" "}
              <a href="#" onClick={(e) => { e.preventDefault(); setMode("login"); }}>
                Sign in
              </a>
            </>
          )}
        </div>

        <div className="mt-16 muted" style={{ fontSize: 12, textAlign: "center" }}>
          Default admin: <code>admin</code> / <code>changeme123</code> (unless changed via env vars)
        </div>
      </div>
    </div>
  );
}
