"use client";

import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import type { AuditLog } from "@/types";

export default function LogViewer() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [page, setPage] = useState(1);
  const [action, setAction] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchLogs = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.logs.list(page, action || undefined);
      setLogs(data.logs);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load logs");
    } finally {
      setLoading(false);
    }
  }, [page, action]);

  useEffect(() => { fetchLogs(); }, [fetchLogs]);

  return (
    <div className="log-viewer">
      <div className="log-viewer__toolbar">
        <input
          className="log-viewer__filter"
          placeholder="Filter by action prefix (e.g. tool:)"
          value={action}
          onChange={(e) => { setAction(e.target.value); setPage(1); }}
        />
        <button className="btn btn--ghost btn--sm" onClick={fetchLogs} disabled={loading}>
          {loading ? "Loading…" : "Refresh"}
        </button>
      </div>

      {error && <p className="log-viewer__error">{error}</p>}

      <table className="log-viewer__table">
        <thead>
          <tr>
            <th>Timestamp</th>
            <th>Action</th>
            <th>Resource</th>
            <th>IP</th>
          </tr>
        </thead>
        <tbody>
          {logs.length === 0 && !loading && (
            <tr>
              <td colSpan={4} className="log-viewer__empty">No log entries.</td>
            </tr>
          )}
          {logs.map((log) => (
            <tr key={log.id} className="log-viewer__row">
              <td className="log-viewer__cell log-viewer__cell--mono">
                {log.created_at.slice(0, 19).replace("T", " ")}
              </td>
              <td className="log-viewer__cell log-viewer__cell--action">{log.action}</td>
              <td className="log-viewer__cell">
                {[log.resource_type, log.resource_id?.slice(0, 8)].filter(Boolean).join(":")}
              </td>
              <td className="log-viewer__cell log-viewer__cell--dim">{log.ip_address ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="log-viewer__pagination">
        <button
          className="btn btn--ghost btn--sm"
          disabled={page <= 1}
          onClick={() => setPage((p) => p - 1)}
        >
          ← Prev
        </button>
        <span>Page {page}</span>
        <button
          className="btn btn--ghost btn--sm"
          disabled={logs.length < 50}
          onClick={() => setPage((p) => p + 1)}
        >
          Next →
        </button>
      </div>
    </div>
  );
}
