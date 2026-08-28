import { describe, expect, it } from "vitest";

import { decodeAccessToken, isTokenExpired } from "./tokens";
import type { AccessTokenPayload } from "./types";

/**
 * jwt-decode only base64-decodes the payload segment — it never verifies
 * the signature — so a fake three-segment string is enough to exercise it
 * without needing a real signing key.
 */
function fakeJwt(payload: AccessTokenPayload): string {
  const segment = (obj: unknown) =>
    Buffer.from(JSON.stringify(obj)).toString("base64url");

  return `${segment({ alg: "none", typ: "JWT" })}.${segment(payload)}.signature`;
}

function futurePayload(overrides: Partial<AccessTokenPayload> = {}): AccessTokenPayload {
  return {
    role: "GUEST",
    user_id: 1,
    exp: Math.floor(Date.now() / 1000) + 3600, // 1h from now
    ...overrides,
  };
}

function pastPayload(overrides: Partial<AccessTokenPayload> = {}): AccessTokenPayload {
  return {
    role: "GUEST",
    user_id: 1,
    exp: Math.floor(Date.now() / 1000) - 3600, // 1h ago
    ...overrides,
  };
}

describe("isTokenExpired", () => {
  it("returns false for a token that expires in the future", () => {
    expect(isTokenExpired(fakeJwt(futurePayload()))).toBe(false);
  });

  it("returns true for a token that already expired", () => {
    expect(isTokenExpired(fakeJwt(pastPayload()))).toBe(true);
  });

  it("returns true for a token expiring inside the safety buffer", () => {
    const almostExpired = fakeJwt(
      futurePayload({ exp: Math.floor(Date.now() / 1000) + 5 })
    );
    expect(isTokenExpired(almostExpired, /* bufferSeconds */ 10)).toBe(true);
  });

  it("returns true for a malformed token instead of throwing", () => {
    expect(isTokenExpired("not-a-real-jwt")).toBe(true);
  });
});

describe("decodeAccessToken", () => {
  it("decodes the payload of a well-formed token", () => {
    const payload = futurePayload({ role: "OPERATOR", user_id: 42 });
    const decoded = decodeAccessToken(fakeJwt(payload));

    expect(decoded).toEqual(payload);
  });

  it("returns null for a malformed token instead of throwing", () => {
    expect(decodeAccessToken("garbage")).toBeNull();
  });
});
