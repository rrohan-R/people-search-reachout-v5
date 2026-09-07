import React from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import ProtectedRoute from "./components/ProtectedRoute";
import Layout from "./components/Layout";

import HomePage from "./pages/Home";
import FAQPage from "./pages/FAQ";
import ContactPage from "./pages/Contact";
import LoginPage from "./pages/Login";
import DashboardPage from "./pages/Dashboard";
import JobsPage from "./pages/JobDescriptions";
import JobDetailPage from "./pages/JobDetail";
import CallsPage from "./pages/CallsDashboard";
import CallDetailPage from "./pages/CallDetail";
import AgentsPage from "./pages/Agents";
import ScheduleCallPage from "./pages/ScheduleCall";
import SchedulesPage from "./pages/Schedules";

export default function App() {
  return (
    <Routes>
      {/* Public / marketing pages */}
      <Route path="/" element={<HomePage />} />
      <Route path="/faq" element={<FAQPage />} />
      <Route path="/contact" element={<ContactPage />} />
      <Route path="/login" element={<LoginPage />} />

      {/* App (protected) */}
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <Layout>
              <DashboardPage />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/jobs"
        element={
          <ProtectedRoute>
            <Layout>
              <JobsPage />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/jobs/:jobId"
        element={
          <ProtectedRoute>
            <Layout>
              <JobDetailPage />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/calls"
        element={
          <ProtectedRoute>
            <Layout>
              <CallsPage />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/calls/:callId"
        element={
          <ProtectedRoute>
            <Layout>
              <CallDetailPage />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/jobs/:jobId/candidates/:candidateId/schedule"
        element={
          <ProtectedRoute>
            <Layout>
              <ScheduleCallPage />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/schedules"
        element={
          <ProtectedRoute>
            <Layout>
              <SchedulesPage />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/schedules/:scheduleId/edit"
        element={
          <ProtectedRoute>
            <Layout>
              <ScheduleCallPage />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/agents"
        element={
          <ProtectedRoute>
            <Layout>
              <AgentsPage />
            </Layout>
          </ProtectedRoute>
        }
      />

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
