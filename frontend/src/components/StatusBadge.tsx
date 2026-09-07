import React from "react";

export default function StatusBadge({ status }: { status?: string | null }) {
  const value = (status || "NOT_STARTED").toLowerCase();
  return <span className={`badge ${value}`}>{(status || "NOT_STARTED").replace(/_/g, " ")}</span>;
}
