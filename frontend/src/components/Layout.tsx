import React from "react";
import { NavLink, Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Layout({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  function handleSignOut(e: React.MouseEvent) {
    e.preventDefault();
    logout();
    navigate("/", { replace: true });
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <Link to="/" className="brand" style={{ textDecoration: "none" }}>
          People<span>Reach</span>
        </Link>
        <NavLink to="/" end className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}>
          Home
        </NavLink>
        <NavLink to="/dashboard" end className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}>
          Dashboard
        </NavLink>
        <NavLink to="/jobs" className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}>
          Job Descriptions
        </NavLink>
        <NavLink to="/calls" className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}>
          Conversations
        </NavLink>
        <NavLink to="/schedules" className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}>
          Schedules
        </NavLink>
        <NavLink to="/agents" className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}>
          Agents
        </NavLink>
      </aside>
      <div className="main-column">
        <div className="topbar">
          <div />
          <div className="topbar-user">
            <span>
              Signed in as <strong>{user?.username}</strong>
            </span>
            <a href="#" onClick={handleSignOut}>
              Sign out
            </a>
          </div>
        </div>
        <main className="main">{children}</main>
      </div>
    </div>
  );
}