"use client";

import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import styles from "./layout.module.css";

const NAV = [
  { href: "/dashboard", label: "OVERVIEW", icon: "◈" },
  { href: "/dashboard/agent", label: "AGENT", icon: "◎" },
  { href: "/dashboard/deployments", label: "DEPLOYS", icon: "⬆" },
  { href: "/dashboard/leads", label: "LEADS", icon: "◉" },
  { href: "/dashboard/content", label: "CONTENT", icon: "▣" },
  { href: "/dashboard/logs", label: "LOGS", icon: "≡" },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const { user, logout, loading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!loading && !user) router.push("/login");
  }, [user, loading, router]);

  if (loading || !user) {
    return (
      <div className={styles.boot}>
        <span className={styles.bootText}>INITIALIZING AGENT SYSTEM...</span>
      </div>
    );
  }

  return (
    <div className={styles.shell}>
      <aside className={styles.sidebar}>
        <div className={styles.brand}>
          <span className={styles.brandIcon}>⬡</span>
          <span className={styles.brandText}>AGENT</span>
        </div>

        <nav className={styles.nav}>
          {NAV.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={`${styles.navItem} ${
                pathname === item.href ? styles.navActive : ""
              }`}
            >
              <span className={styles.navIcon}>{item.icon}</span>
              <span>{item.label}</span>
            </Link>
          ))}
        </nav>

        <div className={styles.sidebarFooter}>
          <div className={styles.userInfo}>
            <span className={styles.userDot} />
            <span className={styles.userEmail}>{user.email}</span>
          </div>
          <button className={styles.logoutBtn} onClick={logout}>
            EXIT
          </button>
        </div>
      </aside>

      <main className={styles.main}>{children}</main>
    </div>
  );
}