"use client";

import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import type { DeployEvent } from "@/types";

const STATUS_COLORS: Record<string, string> = {
  success: "var(--color-green)",
  failed: "var(--color-red)",
  running: "var(--color-yellow)",
  pending: "var(--color-muted)",
};

export default function DeployPanel() {
  const [deploys, setDeploys] = useState<DeployEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [branch, setBranch] = useState("main");

  const fetchDeploys = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.deploy.list(10);
      setDeploys(data.deployments);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load deployments");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchDeploys(); }, [fetchDeploys]);

  async function triggerDeploy() {
    if (!window.confirm(`Deploy branch '${branch}'?`)) return;
    setActionLoading(true);
    setError(null);
    try {
      await api.deploy.trigger(branch, "Manual trigger from dashboard", true);
      await fetchDeploys();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Deploy failed");
    } finally {
      setActionLoading(false);
    }
  }

  async function rollback(deployId: string) {
    if (!window.confirm(`Roll back to deploy ${deployId.slice(0, 8)}?`)) return;
    setActionLoading(true);
    setError(null);
    try {
      await api.deploy.rollback(deployId, "Manual rollback from dashboard", true);
      await fetchDeploys();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Rollback failed");
    } finally {
      setActionLoading(false);
    }
  }

  return (
    <div className="deploy-panel">
      <div className="deploy-panel__toolbar">
        <div className="deploy-panel__trigger-row">
          <input
            className="deploy-panel__branch-input"
            value={branch}
            onChange={(e) => setBranch(e.target.value)}
            placeholder="Branch (e.g. main)"
          />
          <button
            className="btn btn--primary"
            onClick={triggerDeploy}
            disabled={actionLoading || !branch.trim()}
          >
            {actionLoading ? "Deploying…" : "Deploy"}
          </button>
        </div>
        <button className="btn btn--ghost btn--sm" onClick={fetchDeploys} disabled={loading}>
          {loading ? "Loading…" : "Refresh"}
        </button>
      </div>

      {error && <p className="deploy-panel__error">{error}</p>}

      <table className="deploy-panel__table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Status</th>
            <th>Trigger</th>
            <th>SHA</th>
            <th>Started</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {deploys.length === 0 && !loading && (
            <tr>
              <td colSpan={6} className="deploy-panel__empty">No deployments yet.</td>
            </tr>
          )}
          {deploys.map((d) => (
            <tr key={d.id} className="deploy-panel__row">
              <td className="deploy-panel__cell deploy-panel__cell--mono">{d.id.slice(0, 8)}</td>
              <td className="deploy-panel__cell">
                <span style={{ color: STATUS_COLORS[d.status] ?? "inherit" }}>
                  {d.status.toUpperCase()}
                </span>
              </td>
              <td className="deploy-panel__cell">{d.trigger}</td>
              <td className="deploy-panel__cell deploy-panel__cell--mono">
                {d.commit_sha?.slice(0, 7) ?? "—"}
              </td>
              <td className="deploy-panel__cell deploy-panel__cell--dim">
                {d.started_at.slice(0, 19).replace("T", " ")}
              </td>
              <td className="deploy-panel__cell">
                {d.status === "success" && (
                  <button
                    className="btn btn--ghost btn--sm btn--danger"
                    onClick={() => rollback(d.id)}
                    disabled={actionLoading}
                  >
                    Rollback
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
