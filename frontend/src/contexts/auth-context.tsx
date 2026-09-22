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
import { clearOfflineData } from "@/lib/offline";

interface AuthContextValue {
  role: UserRole | null;
  isAuthenticated: boolean;
  /** True until the initial silent-refresh attempt (from the httpOnly cookie) has resolved. */
  isLoading: boolean;
  /**
   * The silent refresh couldn't reach the server (offline reload), so it's
   * unknown whether there is a session. Pages wait instead of redirecting
   * to login; the refresh is retried as soon as the browser is back online.
   */
  isOfflineUnverified: boolean;
  loginAsGuest: (nationalId: string, roomNumber: string) => Promise<void>;
  loginAsOperator: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [tokens, setTokens] = useState<AuthTokens | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isOfflineUnverified, setIsOfflineUnverified] = useState(false);
  const hasRestored = useRef(false);
  const restoreRef = useRef<(() => Promise<void>) | null>(null);

  useEffect(() => {
    // Guards against React StrictMode's double-invoke in development,
    // which would otherwise fire two concurrent refresh calls on mount.
    if (hasRestored.current) return;
    hasRestored.current = true;

    // No access token is ever persisted (not localStorage, not a
    // JS-readable cookie) — on every fresh load we must ask the backend to
    // mint a new one from the httpOnly refresh cookie. A rejection here
    // just means "no active session", not an error.
    const restore = () =>
      restoreSession().then((restored) => {
        setIsOfflineUnverified(restored === "offline");
        setTokens(restored === "offline" ? null : restored);
        setIsLoading(false);
      });
    restore();

    restoreRef.current = restore;

    // An offline reload can't know yet whether there's a session; ask
    // again the moment the network is back.
    const retryWhenOnline = () => {
      restore();
    };
    window.addEventListener("online", retryWhenOnline);

    // Keep React state in sync when the API client silently refreshes (or
    // clears) the access token on its own, mid-request.
    onTokensChanged(setTokens);

    return () => window.removeEventListener("online", retryWhenOnline);
  }, []);

  // The browser's "online" event never fires when it was the server, not
  // the network, that was unreachable — so also retry on a timer while the
  // session is unverified.
  useEffect(() => {
    if (!isOfflineUnverified) return;
    const timer = window.setInterval(() => restoreRef.current?.(), 15_000);
    return () => window.clearInterval(timer);
  }, [isOfflineUnverified]);

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
    // Cached tickets and any queued offline actions belong to this
    // session only — nothing stays on a shared front-desk machine.
    clearOfflineData();
    setTokens(null);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      role: tokens?.role ?? null,
      isAuthenticated: tokens !== null,
      isLoading,
      isOfflineUnverified,
      loginAsGuest,
      loginAsOperator,
      logout,
    }),
    [tokens, isLoading, isOfflineUnverified, loginAsGuest, loginAsOperator, logout]
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
