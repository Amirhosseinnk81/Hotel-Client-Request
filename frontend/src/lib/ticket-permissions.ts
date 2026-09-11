import { getAccessToken } from "@/lib/api/client";
import { decodeAccessToken } from "@/lib/api/tokens";
import type { Ticket } from "@/lib/api/types";

/**
 * Frontend mirror of the backend's operator write rules —
 * IsSupervisor and CanWorkOnOperatorTicket in apps/core/permissions.py.
 *
 * The backend is what actually enforces them; this module only decides
 * which controls to show, so an operator is never offered a button that
 * is guaranteed to come back 403. It has to stay in step with the backend
 * the same way lib/ticket-labels.ts mirrors the status machine, and
 * ticket-permissions.test.ts pins the rules so a one-sided change fails.
 */

export interface OperatorViewer {
  userId: number | null;
  isSupervisor: boolean;
}

/** Reads the logged-in operator from the in-memory access token. */
export function getOperatorViewer(): OperatorViewer {
  const payload = decodeAccessToken(getAccessToken() ?? "");
  return {
    userId: payload?.user_id ?? null,
    isSupervisor: payload?.is_supervisor === true,
  };
}

/** Assigning, reassigning and setting priority are supervisor-only triage. */
export function canTriage(viewer: OperatorViewer): boolean {
  return viewer.isSupervisor;
}

/**
 * Changing a ticket's status — including resolving it — is open to a
 * supervisor, or to the operator the ticket is currently assigned to.
 * An unassigned ticket therefore waits for a supervisor to assign it.
 */
export function canWorkOnTicket(
  ticket: Pick<Ticket, "assigned_to">,
  viewer: OperatorViewer,
): boolean {
  if (viewer.isSupervisor) return true;
  return (
    viewer.userId !== null &&
    ticket.assigned_to != null &&
    ticket.assigned_to === viewer.userId
  );
}
