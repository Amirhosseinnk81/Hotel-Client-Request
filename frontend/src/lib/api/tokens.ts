import { jwtDecode } from "jwt-decode";

import type { AccessTokenPayload } from "./types";

/**
 * The refresh token lives only in an httpOnly cookie set by the backend —
 * this file (and the frontend in general) never sees it, which is the
 * whole point (see apps/core/jwt_cookies.py on the backend). The access
 * token is kept in memory only (see client.ts); nothing here touches
 * localStorage anymore.
 */

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
