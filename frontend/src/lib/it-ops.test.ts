import { describe, expect, it } from "vitest";

import { canMarkProcessDone, isITStaff, isITSupervisor, type ITViewer } from "./it-ops";

// Mirrors IsITStaff / CanWorkOnITItem in apps/core/permissions.py. If one
// of these fails, fix whichever side is actually wrong — the backend
// decides; this module only hides controls that would come back 403.
const itOperator: ITViewer = { userId: 2, role: "OPERATOR", isSupervisor: false, departmentCode: "IT" };
const itSupervisor: ITViewer = { userId: 1, role: "OPERATOR", isSupervisor: true, departmentCode: "IT" };
const hkSupervisor: ITViewer = {
  userId: 3,
  role: "OPERATOR",
  isSupervisor: true,
  departmentCode: "HOUSEKEEPING",
};
const admin: ITViewer = { userId: 9, role: "ADMIN", isSupervisor: false, departmentCode: null };

describe("isITStaff", () => {
  it("lets IT operators and admins in", () => {
    expect(isITStaff(itOperator)).toBe(true);
    expect(isITStaff(itSupervisor)).toBe(true);
    expect(isITStaff(admin)).toBe(true);
  });

  it("keeps other departments out, supervisors included", () => {
    expect(isITStaff(hkSupervisor)).toBe(false);
  });
});

describe("isITSupervisor", () => {
  it("is the IT operator flagged as supervisor, or an admin", () => {
    expect(isITSupervisor(itSupervisor)).toBe(true);
    expect(isITSupervisor(admin)).toBe(true);
    expect(isITSupervisor(itOperator)).toBe(false);
    expect(isITSupervisor(hkSupervisor)).toBe(false);
  });
});

describe("canMarkProcessDone", () => {
  it("lets the responsible operator mark their own process done", () => {
    expect(canMarkProcessDone(itOperator, { responsible: 2 })).toBe(true);
  });

  it("does not let a regular operator mark someone else's", () => {
    expect(canMarkProcessDone(itOperator, { responsible: 5 })).toBe(false);
    expect(canMarkProcessDone(itOperator, { responsible: null })).toBe(false);
  });

  it("lets the IT supervisor mark any process done", () => {
    expect(canMarkProcessDone(itSupervisor, { responsible: 5 })).toBe(true);
  });

  it("never lets a non-IT supervisor do it", () => {
    expect(canMarkProcessDone(hkSupervisor, { responsible: 3 })).toBe(false);
  });
});
