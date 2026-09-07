import { describe, expect, it } from "vitest";

import { normalizeRoomParam } from "./room-param";

describe("normalizeRoomParam", () => {
  it("passes through a plain ASCII room number", () => {
    expect(normalizeRoomParam("305")).toBe("305");
  });

  it("accepts the alphanumeric and hyphenated forms hotels actually use", () => {
    expect(normalizeRoomParam("12B")).toBe("12B");
    expect(normalizeRoomParam("A-4")).toBe("A-4");
  });

  it("folds Persian digits to ASCII", () => {
    // A QR generated from a Persian-language room list carries these;
    // the login API only accepts ASCII.
    expect(normalizeRoomParam("۳۰۵")).toBe("305");
  });

  it("folds Arabic-Indic digits to ASCII", () => {
    expect(normalizeRoomParam("٣٠٥")).toBe("305");
  });

  it("trims surrounding whitespace", () => {
    expect(normalizeRoomParam("  305 ")).toBe("305");
  });

  it("returns empty for a missing param", () => {
    expect(normalizeRoomParam(null)).toBe("");
    expect(normalizeRoomParam(undefined)).toBe("");
    expect(normalizeRoomParam("")).toBe("");
  });

  it("discards anything that isn't shaped like a room number", () => {
    // A malformed link should leave the field empty rather than drop
    // junk into it that the guest then has to clear.
    expect(normalizeRoomParam("305; DROP")).toBe("");
    expect(normalizeRoomParam("<script>")).toBe("");
    expect(normalizeRoomParam("../../etc")).toBe("");
    expect(normalizeRoomParam("30000000000")).toBe("");
  });
});
