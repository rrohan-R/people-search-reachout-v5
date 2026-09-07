import React from "react";
import { NavLink } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Layout({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth();

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          People<span>Reach</span>
        </div>
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
            <a href="#" onClick={(e) => { e.preventDefault(); logout(); }}>
              Sign out
            </a>
          </div>
        </div>
        <main className="main">{children}</main>
      </div>
    </div>
  );
}
