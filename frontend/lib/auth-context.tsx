"use client";

import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "./api";
import type { AuthOut } from "@/types/api";

interface Session {
  token: string;
  userId: string;
  email: string;
  organizationId: string;
  organizationName: string;
}

interface AuthContextValue {
  session: Session | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (
    email: string,
    password: string,
    organizationName: string,
    displayName: string
  ) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function saveSession(auth: AuthOut): Session {
  if (typeof window !== "undefined") {
    window.localStorage.setItem("synthetix_token", auth.token);
    window.localStorage.setItem("synthetix_org_id", auth.organization_id);
    window.localStorage.setItem(
      "synthetix_session",
      JSON.stringify({
        userId: auth.user_id,
        email: auth.email,
        organizationId: auth.organization_id,
        organizationName: auth.organization_name,
      })
    );
  }
  return {
    token: auth.token,
    userId: auth.user_id,
    email: auth.email,
    organizationId: auth.organization_id,
    organizationName: auth.organization_name,
  };
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const raw = window.localStorage.getItem("synthetix_session");
    const token = window.localStorage.getItem("synthetix_token");
    if (raw && token) {
      try {
        const parsed = JSON.parse(raw);
        setSession({ token, ...parsed });
      } catch {
        // ignore corrupt local storage
      }
    }
    setLoading(false);
  }, []);

  const login = async (email: string, password: string) => {
    const auth = await api.post<AuthOut>("/api/auth/login", { email, password });
    setSession(saveSession(auth));
  };

  const signup = async (
    email: string,
    password: string,
    organizationName: string,
    displayName: string
  ) => {
    const auth = await api.post<AuthOut>("/api/auth/signup", {
      email,
      password,
      organization_name: organizationName,
      display_name: displayName,
    });
    setSession(saveSession(auth));
  };

  const logout = () => {
    window.localStorage.removeItem("synthetix_token");
    window.localStorage.removeItem("synthetix_org_id");
    window.localStorage.removeItem("synthetix_session");
    setSession(null);
  };

  return (
    <AuthContext.Provider value={{ session, loading, login, signup, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

export function useDemoLogin() {
  const { login } = useAuth();
  return async () => {
    await login("demo@synthetixhr.example", "SynthetixDemo!1");
  };
}

export { ApiError };
