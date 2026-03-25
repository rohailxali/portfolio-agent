"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { DeployEvent } from "@/types";
import styles from "../page.module.css";

export default function DeploymentsPage() {
  const [deploys, setDeploys] = useState<DeployEvent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.deploy.list(20)
      .then((d) => setDeploys((d as any).deployments || []))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div style={{ padding: "32px" }}>
      <h1 style={{
        fontFamily: "var(--font-display)",
        fontSize: "22px",
        fontWeight: 800,
        letterSpacing: "0.08em",
        marginBottom: "24px"
      }}>
        DEPLOYMENTS
      </h1>

      {loading ? (
        <p style={{ color: "var(--text-muted)" }}>LOADING...</p>
      ) : (
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>
              {["ID", "STATUS", "TRIGGER", "SHA", "STARTED"].map((h) => (
                <th key={h} style={{
                  textAlign: "left",
                  padding: "10px 16px",
                  fontSize: "10px",
                  letterSpacing: "0.1em",
                  color: "var(--text-muted)",
                  borderBottom: "1px solid var(--border)"
                }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {deploys.length === 0 && (
              <tr>
                <td colSpan={5} style={{
                  padding: "32px",
                  textAlign: "center",
                  color: "var(--text-muted)"
                }}>
                  No deployments yet
                </td>
              </tr>
            )}
            {deploys.map((d) => (
              <tr key={d.id}>
                <td style={{ padding: "10px 16px", fontSize: "12px",
                  color: "var(--accent-blue)" }}>{d.id.slice(0, 8)}</td>
                <td style={{ padding: "10px 16px", fontSize: "12px",
                  color: d.status === "success" ? "var(--accent-green)" :
                         d.status === "failed" ? "var(--accent-red)" :
                         "var(--accent-amber)" }}>{d.status}</td>
                <td style={{ padding: "10px 16px", fontSize: "12px",
                  color: "var(--text-secondary)" }}>{d.trigger}</td>
                <td style={{ padding: "10px 16px", fontSize: "12px",
                  color: "var(--text-muted)" }}>{d.commit_sha?.slice(0, 7) || "—"}</td>
                <td style={{ padding: "10px 16px", fontSize: "12px",
                  color: "var(--text-muted)" }}>{new Date(d.started_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
} 