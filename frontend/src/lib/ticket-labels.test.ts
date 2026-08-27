import { describe, expect, it } from "vitest";

import {
  priorityBadgeVariant,
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
});
