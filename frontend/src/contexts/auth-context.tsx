"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

import {
  loginGuest,
  loginOperator,
  logout as logoutApi,
  onTokensChanged,
  restoreSession,
} from "@/lib/api/client";
import type { AuthTokens, UserRole } from "@/lib/api/types";

interface AuthContextValue {
  role: UserRole | null;
  isAuthenticated: boolean;
  /** True until the initial silent-refresh attempt (from the httpOnly cookie) has resolved. */
  isLoading: boolean;
  loginAsGuest: (nationalId: string, roomNumber: string) => Promise<void>;
  loginAsOperator: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [tokens, setTokens] = useState<AuthTokens | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const hasRestored = useRef(false);

  useEffect(() => {
    // Guards against React StrictMode's double-invoke in development,
    // which would otherwise fire two concurrent refresh calls on mount.
    if (hasRestored.current) return;
    hasRestored.current = true;

    // No access token is ever persisted (not localStorage, not a
    // JS-readable cookie) — on every fresh load we must ask the backend to
    // mint a new one from the httpOnly refresh cookie. A rejection here
    // just means "no active session", not an error.
    restoreSession().then((restored) => {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setTokens(restored);
      setIsLoading(false);
    });

    // Keep React state in sync when the API client silently refreshes (or
    // clears) the access token on its own, mid-request.
    onTokensChanged(setTokens);
  }, []);

  const loginAsGuest = useCallback(async (nationalId: string, roomNumber: string) => {
    const newTokens = await loginGuest(nationalId, roomNumber);
    setTokens(newTokens);
  }, []);

  const loginAsOperator = useCallback(async (username: string, password: string) => {
    const newTokens = await loginOperator(username, password);
    setTokens(newTokens);
  }, []);

  const logout = useCallback(async () => {
    await logoutApi();
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
