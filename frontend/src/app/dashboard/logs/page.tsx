"use client";

import { useEffect, useState } from "react";
import { api } from "../../../lib/api";
import type { AuditLog } from "../../../types";
import styles from "./logs.module.css";

export default function LogsPage() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [filter, setFilter] = useState("");

  const load = () => {
    setLoading(true);
    api.logs
      .list(page, filter || undefined)
      .then((res) => setLogs(res.logs))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [page, filter]);

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}>AUDIT LOG</h1>
        <div className={styles.controls}>
          <input
            className={styles.search}
            placeholder="Filter by action prefix…"
            value={filter}
            onChange={(e) => { setFilter(e.target.value); setPage(1); }}
          />
        </div>
      </header>

      <div className={styles.logList}>
        {loading ? (
          <div className={styles.loading}>FETCHING LOGS...</div>
        ) : logs.length === 0 ? (
          <div className={styles.empty}>No log entries found.</div>
        ) : (
          logs.map((log) => (
            <div key={log.id} className={styles.entry}>
              <span className={styles.ts}>
                {new Date(log.created_at).toLocaleString()}
              </span>
              <span className={styles.action}>{log.action}</span>
              {log.resource_type && (
                <span className={styles.resource}>
                  {log.resource_type}
                  {log.resource_id ? `:${log.resource_id.slice(0, 8)}` : ""}
                </span>
              )}
              {log.ip_address && (
                <span className={styles.ip}>{log.ip_address}</span>
              )}
              {log.meta && (
                <details className={styles.meta}>
                  <summary>meta</summary>
                  <pre>{JSON.stringify(log.meta, null, 2)}</pre>
                </details>
              )}
            </div>
          ))
        )}
      </div>

      <div className={styles.pagination}>
        <button
          className={styles.pageBtn}
          onClick={() => setPage((p) => Math.max(1, p - 1))}
          disabled={page === 1}
        >
          ← PREV
        </button>
        <span className={styles.pageNum}>PAGE {page}</span>
        <button
          className={styles.pageBtn}
          onClick={() => setPage((p) => p + 1)}
          disabled={logs.length < 50}
        >
          NEXT →
        </button>
      </div>
    </div>
  );
}