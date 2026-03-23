"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { HealthStatus } from "@/types";

export default function StatusPanel() {
  const [status, setStatus] = useState<HealthStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function fetchStatus() {
    setLoading(true);
    setError(null);
    try {
      const data = await api.monitor.status();
      setStatus(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load status");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 60_000);
    return () => clearInterval(interval);
  }, []);

  if (loading && !status) {
    return <div className="status-panel status-panel--loading">Checking site health…</div>;
  }

  if (error) {
    return <div className="status-panel status-panel--error">{error}</div>;
  }

  if (!status) return null;

  const isUp = status.is_up;
  const stateClass = isUp ? "status-panel--up" : "status-panel--down";
  const indicator = isUp ? "● ONLINE" : "● OFFLINE";

  return (
    <div className={`status-panel ${stateClass}`}>
      <div className="status-panel__header">
        <span className="status-panel__indicator">{indicator}</span>
        <button className="btn btn--ghost btn--sm" onClick={fetchStatus} disabled={loading}>
          {loading ? "Refreshing…" : "Refresh"}
        </button>
      </div>

      <div className="status-panel__grid">
        <div className="status-panel__item">
          <span className="status-panel__label">URL</span>
          <span className="status-panel__value">{status.url}</span>
        </div>
        <div className="status-panel__item">
          <span className="status-panel__label">HTTP Status</span>
          <span className="status-panel__value">{status.status_code ?? "—"}</span>
        </div>
        <div className="status-panel__item">
          <span className="status-panel__label">Response Time</span>
          <span className="status-panel__value">
            {status.response_time_ms != null ? `${status.response_time_ms} ms` : "—"}
          </span>
        </div>
        <div className="status-panel__item">
          <span className="status-panel__label">SSL Expiry</span>
          <span
            className={`status-panel__value ${
              status.ssl_expiry_days != null && status.ssl_expiry_days < 14
                ? "status-panel__value--warn"
                : ""
            }`}
          >
            {status.ssl_expiry_days != null ? `${status.ssl_expiry_days} days` : "—"}
          </span>
        </div>
        {status.error && (
          <div className="status-panel__item status-panel__item--full">
            <span className="status-panel__label">Error</span>
            <span className="status-panel__value status-panel__value--error">{status.error}</span>
          </div>
        )}
      </div>
    </div>
  );
}
