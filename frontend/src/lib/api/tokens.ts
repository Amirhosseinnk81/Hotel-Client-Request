import { jwtDecode } from "jwt-decode";

import type { AccessTokenPayload, AuthTokens } from "./types";

const STORAGE_KEY = "hotel_auth_tokens";

/**
 * All token storage lives in localStorage. This is the simple choice for
 * an MVP — it's easier to reason about than httpOnly cookies + CSRF
 * handling, at the cost of being more exposed to XSS. Worth revisiting
 * before a real production deployment.
 */
export function saveTokens(tokens: AuthTokens): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(tokens));
}

export function getStoredTokens(): AuthTokens | null {
  if (typeof window === "undefined") return null;

  const raw = window.localStorage.getItem(STORAGE_KEY);
  if (!raw) return null;

  try {
    return JSON.parse(raw) as AuthTokens;
  } catch {
    return null;
  }
}

export function clearTokens(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(STORAGE_KEY);
}

/** True if the token is missing, malformed, or expired (with a small buffer). */
export function isTokenExpired(token: string, bufferSeconds = 10): boolean {
  try {
    const { exp } = jwtDecode<AccessTokenPayload>(token);
    return Date.now() >= (exp - bufferSeconds) * 1000;
  } catch {
    return true;
  }
}

export function decodeAccessToken(token: string): AccessTokenPayload | null {
  try {
    return jwtDecode<AccessTokenPayload>(token);
  } catch {
    return null;
  }
}