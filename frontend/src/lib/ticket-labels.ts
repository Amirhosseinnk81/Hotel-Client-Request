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
 * Business rule: OPEN → IN_PROGRESS → RESOLVED, or OPEN/IN_PROGRESS →
 * CANCELLED. Single source of truth — shared by the ticket detail page's
 * status Select and the Kanban board's drag targets (Stage 2.10), so the
 * two can never silently drift apart.
 */
export const allowedNextStatuses: Record<TicketStatus, TicketStatus[]> = {
  OPEN: ["IN_PROGRESS", "CANCELLED"],
  IN_PROGRESS: ["RESOLVED", "CANCELLED"],
  RESOLVED: [],
  CANCELLED: [],
};
