import { ArrowDown, ArrowUp, Flame, Minus, type LucideIcon } from "lucide-react";

import type { TicketPriority, TicketStatus } from "@/lib/api/types";

export const statusLabels: Record<TicketStatus, string> = {
  OPEN: "باز",
  IN_PROGRESS: "در حال بررسی",
  RESOLVED: "حل‌شده",
  CANCELLED: "لغوشده",
};

export const statusBadgeVariant: Record<
  TicketStatus,
  "default" | "warning" | "success" | "secondary"
> = {
  OPEN: "default",
  IN_PROGRESS: "warning",
  RESOLVED: "success",
  CANCELLED: "secondary",
};

export const priorityLabels: Record<TicketPriority, string> = {
  LOW: "کم",
  NORMAL: "عادی",
  HIGH: "زیاد",
  URGENT: "فوری",
};

export const priorityBadgeVariant: Record<
  TicketPriority,
  "secondary" | "default" | "warning" | "destructive"
> = {
  LOW: "secondary",
  NORMAL: "default",
  HIGH: "warning",
  URGENT: "destructive",
};

/**
 * Stage 2.5 — priority icon shown alongside the label on every ticket
 * card, so priority is scannable at a glance without reading text.
 * ArrowDown/Minus/ArrowUp read as an intensity ramp; URGENT breaks the
 * pattern deliberately (Flame) so it doesn't blend in as "just a bigger
 * arrow" next to HIGH.
 */
export const priorityIcons: Record<TicketPriority, LucideIcon> = {
  LOW: ArrowDown,
  NORMAL: Minus,
  HIGH: ArrowUp,
  URGENT: Flame,
};

/**
 * Business rule: OPEN → IN_PROGRESS → RESOLVED, with CANCELLED reachable
 * only from OPEN, and IN_PROGRESS able to drop back to OPEN (an operator
 * who picked a ticket up by mistake, or is handing it back to the queue).
 *
 * This MUST stay a mirror of `Ticket.ALLOWED_STATUS_TRANSITIONS` in
 * apps/tickets/models.py — the backend is what actually enforces it, and
 * anything offered here that the backend rejects turns into a 400 the
 * user can't do anything about. Notably CANCELLED is NOT reachable from
 * IN_PROGRESS — a ticket has to be cancelled while it's still OPEN, or
 * else be resolved.
 *
 * Single source of truth on the frontend side — shared by the ticket
 * detail page's status Select and the Kanban board's drag targets
 * (Stage 2.10), so those two can never drift apart either.
 */
export const allowedNextStatuses: Record<TicketStatus, TicketStatus[]> = {
  OPEN: ["IN_PROGRESS", "CANCELLED"],
  IN_PROGRESS: ["RESOLVED", "OPEN"],
  RESOLVED: [],
  CANCELLED: [],
};
