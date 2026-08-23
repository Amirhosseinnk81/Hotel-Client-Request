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
