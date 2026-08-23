"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { loginGuest, loginOperator, onTokensChanged } from "@/lib/api/client";
import { clearTokens, getStoredTokens, saveTokens } from "@/lib/api/tokens";
import type { AuthTokens, UserRole } from "@/lib/api/types";

interface AuthContextValue {
  role: UserRole | null;
  isAuthenticated: boolean;
  /** True until the initial read from localStorage has happened (avoids a login-page flash). */
  isLoading: boolean;
  loginAsGuest: (nationalId: string, roomNumber: string) => Promise<void>;
  loginAsOperator: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [tokens, setTokens] = useState<AuthTokens | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Reading localStorage must happen post-mount (it doesn't exist during
    // SSR) to avoid a hydration mismatch — this is the standard pattern for
    // syncing initial client-only state, not a case the lint rule intends.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setTokens(getStoredTokens());
    setIsLoading(false);

    // Keep in-memory state in sync when the API client silently refreshes
    // (or clears) tokens on its own, mid-request.
    onTokensChanged(setTokens);
  }, []);

  const loginAsGuest = useCallback(async (nationalId: string, roomNumber: string) => {
    const newTokens = await loginGuest(nationalId, roomNumber);
    saveTokens(newTokens);
    setTokens(newTokens);
  }, []);

  const loginAsOperator = useCallback(async (username: string, password: string) => {
    const newTokens = await loginOperator(username, password);
    saveTokens(newTokens);
    setTokens(newTokens);
  }, []);

  const logout = useCallback(() => {
    clearTokens();
    setTokens(null);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      role: tokens?.role ?? null,
      isAuthenticated: tokens !== null,
      isLoading,
      loginAsGuest,
      loginAsOperator,
      logout,
    }),
    [tokens, isLoading, loginAsGuest, loginAsOperator, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
