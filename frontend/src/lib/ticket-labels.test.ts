import { describe, expect, it } from "vitest";

import {
  allowedNextStatuses,
  priorityBadgeVariant,
  priorityIcons,
  priorityLabels,
  statusBadgeVariant,
  statusLabels,
} from "./ticket-labels";
import type { TicketPriority, TicketStatus } from "@/lib/api/types";

// Hard-coded on purpose: TicketStatus/TicketPriority are compile-time-only
// types (erased at runtime), so this list is the only thing standing
// between "someone adds a new status to the backend" and "the UI silently
// renders `undefined` for it". If this test fails after a backend change,
// the fix is to add the new key to every map below, not to this list.
const allStatuses: TicketStatus[] = ["OPEN", "IN_PROGRESS", "RESOLVED", "CANCELLED"];
const allPriorities: TicketPriority[] = ["LOW", "NORMAL", "HIGH", "URGENT"];

describe("ticket status labels", () => {
  it("has a Persian label for every status", () => {
    for (const status of allStatuses) {
      expect(statusLabels[status]).toBeTruthy();
    }
  });

  it("has a badge variant for every status", () => {
    for (const status of allStatuses) {
      expect(statusBadgeVariant[status]).toBeTruthy();
    }
  });
});

describe("ticket priority labels", () => {
  it("has a Persian label for every priority", () => {
    for (const priority of allPriorities) {
      expect(priorityLabels[priority]).toBeTruthy();
    }
  });

  it("has a badge variant for every priority", () => {
    for (const priority of allPriorities) {
      expect(priorityBadgeVariant[priority]).toBeTruthy();
    }
  });

  it("has an icon for every priority", () => {
    for (const priority of allPriorities) {
      expect(priorityIcons[priority]).toBeTruthy();
    }
  });
});

describe("allowed status transitions", () => {
  // Transcribed from Ticket.ALLOWED_STATUS_TRANSITIONS in
  // apps/tickets/models.py. The backend is the enforcing side, so this
  // test exists to catch the two ways the UI can drift from it: offering
  // a transition the API rejects with a 400 (a dead button the user
  // can't get past), or hiding one the API allows. If this fails, change
  // whichever side is actually wrong — don't just update the expectation.
  const backendTransitions: Record<TicketStatus, TicketStatus[]> = {
    OPEN: ["IN_PROGRESS", "CANCELLED"],
    IN_PROGRESS: ["RESOLVED", "OPEN"],
    RESOLVED: [],
    CANCELLED: [],
  };

  it("matches the backend state machine exactly", () => {
    for (const status of allStatuses) {
      expect([...allowedNextStatuses[status]].sort()).toEqual(
        [...backendTransitions[status]].sort(),
      );
    }
  });

  it("never offers a transition out of a terminal status", () => {
    expect(allowedNextStatuses.RESOLVED).toEqual([]);
    expect(allowedNextStatuses.CANCELLED).toEqual([]);
  });

  it("does not offer CANCELLED from IN_PROGRESS", () => {
    // Regression: the UI used to show a Cancel option here that the
    // backend always rejected. Cancelling is only reachable from OPEN.
    expect(allowedNextStatuses.IN_PROGRESS).not.toContain("CANCELLED");
  });
});
