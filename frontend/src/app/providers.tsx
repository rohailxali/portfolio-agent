"use client";

import { useState, useEffect, useCallback } from "react";
import { AuthContext } from "../lib/auth";
import { api, setToken, getToken } from "../lib/api";
import type { User } from "../types";

export function Providers({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setTokenState] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  // Attempt silent refresh on mount
  useEffect(() => {
    (async () => {
      try {
        const res = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1"}/auth/refresh`,
          { method: "POST", credentials: "include" }
        );
        if (res.ok) {
          const data = await res.json();
          setToken(data.access_token);
          setTokenState(data.access_token);
          const me = await api.auth.me();
          setUser(me as User);
        }
      } catch {
        // Not authenticated; show login
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const data = await api.auth.login(email, password);
    setToken(data.access_token);
    setTokenState(data.access_token);
    const me = await api.auth.me();
    setUser(me as User);
  }, []);

  const logout = useCallback(async () => {
    await api.auth.logout();
    setToken(null);
    setTokenState(null);
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, token, login, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
}