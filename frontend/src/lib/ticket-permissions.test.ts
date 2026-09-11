import { describe, expect, it } from "vitest";

import { canTriage, canWorkOnTicket } from "./ticket-permissions";

// Mirrors IsSupervisor / CanWorkOnOperatorTicket in
// apps/core/permissions.py. If one of these fails, change whichever side
// is actually wrong — the backend decides; this module only hides
// controls that would otherwise come back 403.
const supervisor = { userId: 1, isSupervisor: true };
const operator = { userId: 2, isSupervisor: false };

describe("canTriage", () => {
  it("lets a supervisor assign tickets and set priority", () => {
    expect(canTriage(supervisor)).toBe(true);
  });

  it("keeps regular operators out of assignment and priority", () => {
    expect(canTriage(operator)).toBe(false);
  });
});

describe("canWorkOnTicket", () => {
  it("lets a regular operator work on a ticket assigned to them", () => {
    expect(canWorkOnTicket({ assigned_to: 2 }, operator)).toBe(true);
  });

  it("refuses a regular operator a ticket assigned to a colleague", () => {
    expect(canWorkOnTicket({ assigned_to: 3 }, operator)).toBe(false);
  });

  it("refuses a regular operator an unassigned ticket, which waits for a supervisor", () => {
    expect(canWorkOnTicket({ assigned_to: null }, operator)).toBe(false);
    expect(canWorkOnTicket({}, operator)).toBe(false);
  });

  it("lets a supervisor work on any department ticket, assigned or not", () => {
    expect(canWorkOnTicket({ assigned_to: 3 }, supervisor)).toBe(true);
    expect(canWorkOnTicket({ assigned_to: null }, supervisor)).toBe(true);
  });

  it("never matches when the viewer's id is unknown", () => {
    // A missing or garbled token decodes to userId null — that must not
    // accidentally "match" an unassigned ticket's null assignee.
    expect(canWorkOnTicket({ assigned_to: null }, { userId: null, isSupervisor: false })).toBe(
      false,
    );
  });
});
