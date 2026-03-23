"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Lead } from "@/types";
import styles from "./leads.module.css";

const STATUS_ORDER = ["new", "classified", "contacted", "converted", "spam"];

export default function LeadsPage() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [filter, setFilter] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [classifying, setClassifying] = useState<string | null>(null);

  const load = (status?: string) => {
    setLoading(true);
    api.leads
      .list(1, status || undefined)
      .then((l) => setLeads(l as Lead[]))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load(filter);
  }, [filter]);

  async function classify(id: string) {
    setClassifying(id);
    try {
      await api.leads.classify(id);
      load(filter);
    } finally {
      setClassifying(null);
    }
  }

  async function updateStatus(id: string, status: string) {
    await api.leads.updateStatus(id, status);
    load(filter);
  }

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}>LEADS</h1>
        <div className={styles.filters}>
          {["", ...STATUS_ORDER].map((s) => (
            <button
              key={s}
              className={`${styles.filterBtn} ${filter === s ? styles.filterActive : ""}`}
              onClick={() => setFilter(s)}
            >
              {s || "ALL"}
            </button>
          ))}
        </div>
      </header>

      {loading ? (
        <div className={styles.loading}>LOADING LEADS...</div>
      ) : (
        <table className={styles.table}>
          <thead>
            <tr>
              <th>NAME</th>
              <th>EMAIL</th>
              <th>MESSAGE</th>
              <th>CLASS</th>
              <th>STATUS</th>
              <th>DATE</th>
              <th>ACTIONS</th>
            </tr>
          </thead>
          <tbody>
            {leads.length === 0 && (
              <tr>
                <td colSpan={7} className={styles.empty}>
                  No leads found
                </td>
              </tr>
            )}
            {leads.map((lead) => (
              <tr key={lead.id}>
                <td className={styles.name}>{lead.name}</td>
                <td className={styles.email}>{lead.email}</td>
                <td className={styles.message}>
                  {lead.message ? (
                    <span title={lead.message}>
                      {lead.message.slice(0, 60)}
                      {lead.message.length > 60 ? "…" : ""}
                    </span>
                  ) : (
                    <span className={styles.none}>—</span>
                  )}
                </td>
                <td>
                  {lead.classification ? (
                    <span
                      className={styles.classChip}
                      data-class={lead.classification}
                    >
                      {lead.classification.toUpperCase()}
                    </span>
                  ) : (
                    <span className={styles.none}>—</span>
                  )}
                </td>
                <td>
                  <select
                    className={styles.statusSelect}
                    value={lead.status}
                    onChange={(e) => updateStatus(lead.id, e.target.value)}
                  >
                    {STATUS_ORDER.map((s) => (
                      <option key={s} value={s}>
                        {s}
                      </option>
                    ))}
                  </select>
                </td>
                <td className={styles.date}>
                  {new Date(lead.created_at).toLocaleDateString()}
                </td>
                <td>
                  {!lead.classification && (
                    <button
                      className={styles.actionBtn}
                      onClick={() => classify(lead.id)}
                      disabled={classifying === lead.id}
                    >
                      {classifying === lead.id ? "…" : "CLASSIFY"}
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}