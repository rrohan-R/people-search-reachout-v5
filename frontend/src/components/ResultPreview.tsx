import React from "react";

function humanizeKey(key: string) {
  return key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatValue(value: any): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

/**
 * Compact, at-a-glance rendering of a call's structured result (the answers
 * the agent captured), for use in table rows. Shows the first field clearly
 * plus a count of any remaining ones; full detail lives on the call page.
 */
export default function ResultPreview({ result }: { result?: Record<string, any> | null }) {
  const RESERVED_KEYS = new Set(["error", "details", "info"]);
  const entries = Object.entries(result || {}).filter(([key]) => !RESERVED_KEYS.has(key));

  if (entries.length === 0) {
    if (result?.error) {
      return (
        <span className="result-preview" style={{ color: "var(--danger)" }} title={String(result.error)}>
          Call failed — {String(result.error)}
        </span>
      );
    }
    if (result?.info) {
      return <span className="result-preview empty" title={String(result.info)}>{String(result.info)}</span>;
    }
    return <span className="result-preview empty">No response captured yet</span>;
  }

  const [firstKey, firstValue] = entries[0];
  const remaining = entries.length - 1;

  return (
    <span className="result-preview" title={entries.map(([k, v]) => `${humanizeKey(k)}: ${formatValue(v)}`).join(" · ")}>
      <strong>{humanizeKey(firstKey)}:</strong> {formatValue(firstValue)}
      {remaining > 0 ? ` · +${remaining} more` : ""}
    </span>
  );
}
