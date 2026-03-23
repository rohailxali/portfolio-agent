"use client";

import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import type { Lead } from "@/types";

const STATUS_OPTIONS = ["", "new", "classified", "contacted", "converted", "spam"];
const CLASS_COLORS: Record<string, string> = {
  hot: "var(--color-red)",
  warm: "var(--color-yellow)",
  cold: "var(--color-blue)",
  spam: "var(--color-muted)",
};

export default function LeadsTable() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchLeads = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.leads.list(page, statusFilter || undefined);
      setLeads(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load leads");
    } finally {
      setLoading(false);
    }
  }, [page, statusFilter]);

  useEffect(() => { fetchLeads(); }, [fetchLeads]);

  async function classify(id: string) {
    try {
      await api.leads.classify(id);
      fetchLeads();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Classification failed");
    }
  }

  async function updateStatus(id: string, status: string) {
    try {
      await api.leads.updateStatus(id, status);
      fetchLeads();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Status update failed");
    }
  }

  return (
    <div className="leads-table">
      <div className="leads-table__toolbar">
        <select
          className="leads-table__filter"
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
        >
          {STATUS_OPTIONS.map((s) => (
            <option key={s} value={s}>{s || "All statuses"}</option>
          ))}
        </select>
        <button className="btn btn--ghost btn--sm" onClick={fetchLeads} disabled={loading}>
          {loading ? "Loading…" : "Refresh"}
        </button>
      </div>

      {error && <p className="leads-table__error">{error}</p>}

      <table className="leads-table__table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Email</th>
            <th>Classification</th>
            <th>Status</th>
            <th>Date</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {leads.length === 0 && !loading && (
            <tr>
              <td colSpan={6} className="leads-table__empty">No leads found.</td>
            </tr>
          )}
          {leads.map((lead) => (
            <tr key={lead.id} className="leads-table__row">
              <td className="leads-table__cell">{lead.name}</td>
              <td className="leads-table__cell leads-table__cell--mono">{lead.email}</td>
              <td className="leads-table__cell">
                {lead.classification ? (
                  <span
                    className="leads-table__badge"
                    style={{ color: CLASS_COLORS[lead.classification] ?? "inherit" }}
                  >
                    {lead.classification.toUpperCase()}
                  </span>
                ) : (
                  <span className="leads-table__badge leads-table__badge--muted">—</span>
                )}
              </td>
              <td className="leads-table__cell">
                <select
                  value={lead.status}
                  onChange={(e) => updateStatus(lead.id, e.target.value)}
                  className="leads-table__status-select"
                >
                  {["new", "classified", "contacted", "converted", "spam"].map((s) => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              </td>
              <td className="leads-table__cell leads-table__cell--dim">
                {lead.created_at.slice(0, 10)}
              </td>
              <td className="leads-table__cell">
                <button
                  className="btn btn--ghost btn--sm"
                  onClick={() => classify(lead.id)}
                >
                  Classify
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="leads-table__pagination">
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
          disabled={leads.length < 20}
          onClick={() => setPage((p) => p + 1)}
        >
          Next →
        </button>
      </div>
    </div>
  );
}
