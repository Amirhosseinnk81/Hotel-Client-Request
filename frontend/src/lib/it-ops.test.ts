import { describe, expect, it } from "vitest";

import {
  canCreateItItem,
  canDeleteItItem,
  canEditItItem,
  canMarkProcessDone,
  changedFields,
  isItFieldEditable,
  isITStaff,
  isITSupervisor,
  isoToLocalInput,
  itRequestStatusOptions,
  localInputToIso,
  type ITViewer,
} from "./it-ops";

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

describe("create / edit / delete", () => {
  it("regular IT operators create only tasks and department requests", () => {
    expect(canCreateItItem(itOperator, "tasks")).toBe(true);
    expect(canCreateItItem(itOperator, "department-requests")).toBe(true);
    expect(canCreateItItem(itOperator, "projects")).toBe(false);
    expect(canCreateItItem(itOperator, "processes")).toBe(false);
    expect(canCreateItItem(itSupervisor, "projects")).toBe(true);
    expect(canCreateItItem(hkSupervisor, "tasks")).toBe(false);
  });

  it("regular IT operators edit only what is assigned to them", () => {
    expect(canEditItItem(itOperator, "tasks", { assigned_to: 2 })).toBe(true);
    expect(canEditItItem(itOperator, "tasks", { assigned_to: 5 })).toBe(false);
    expect(canEditItItem(itOperator, "projects", { assigned_to: 2 })).toBe(false);
    expect(canEditItItem(itSupervisor, "tasks", { assigned_to: 5 })).toBe(true);
  });

  it("only the supervisor deletes", () => {
    expect(canDeleteItItem(itSupervisor)).toBe(true);
    expect(canDeleteItItem(admin)).toBe(true);
    expect(canDeleteItItem(itOperator)).toBe(false);
  });

  it("hides assignment always, and priority once the item exists, from regular operators", () => {
    expect(isItFieldEditable(itOperator, "tasks", "assigned_to", "create")).toBe(false);
    expect(isItFieldEditable(itOperator, "tasks", "priority", "create")).toBe(true);
    expect(isItFieldEditable(itOperator, "tasks", "priority", "edit")).toBe(false);
    expect(isItFieldEditable(itOperator, "tasks", "status", "edit")).toBe(true);
    expect(isItFieldEditable(itSupervisor, "tasks", "assigned_to", "edit")).toBe(true);
  });

  it("keeps REJECTED for the supervisor", () => {
    expect(itRequestStatusOptions(itOperator)).not.toContain("REJECTED");
    expect(itRequestStatusOptions(itSupervisor)).toContain("REJECTED");
  });
});

describe("changedFields", () => {
  it("sends only what changed, so an untouched priority never reaches the server", () => {
    const original = { title: "Fix", priority: "HIGH", due_date: null };
    const values = { title: "Fix switch", priority: "HIGH", due_date: null };

    expect(changedFields(original, values)).toEqual({ title: "Fix switch" });
  });

  it("treats empty and null as the same", () => {
    expect(changedFields({ assigned_to: null }, { assigned_to: undefined })).toEqual({});
  });
});

describe("datetime-local round trip", () => {
  it("converts back and forth", () => {
    const iso = localInputToIso("2026-09-22T14:30");
    expect(iso).not.toBeNull();
    expect(isoToLocalInput(iso)).toBe("2026-09-22T14:30");
    expect(localInputToIso("")).toBeNull();
    expect(isoToLocalInput(null)).toBe("");
  });
});
