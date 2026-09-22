import { getAccessToken } from "@/lib/api/client";
import { decodeAccessToken } from "@/lib/api/tokens";
import type {
  AccessTokenPayload,
  ITPriority,
  ITProcess,
  ITProcessFrequency,
  ITProcessType,
  ITRequestStatus,
  ITTaskStatus,
} from "@/lib/api/types";

/**
 * IT Ops labels and the frontend mirror of its access rules —
 * IsITStaff / CanWorkOnITItem in apps/core/permissions.py. As with
 * lib/ticket-permissions.ts, the backend enforces; this only decides which
 * links and buttons to show. it-ops.test.ts pins the rules.
 */

/**
 * Must match settings.IT_DEPARTMENT_CODE on the backend (default "IT").
 * If a hotel changes it there, the IT link simply stays hidden until this
 * is changed too — the endpoints themselves keep working.
 */
export const IT_DEPARTMENT_CODE = "IT";

export const itPriorityLabels: Record<ITPriority, string> = {
  LOW: "کم",
  MEDIUM: "متوسط",
  HIGH: "زیاد",
  CRITICAL: "بحرانی",
};

export const itTaskStatusLabels: Record<ITTaskStatus, string> = {
  TODO: "انجام‌نشده",
  IN_PROGRESS: "در حال انجام",
  DONE: "انجام‌شده",
  BLOCKED: "متوقف",
};

export const itRequestStatusLabels: Record<ITRequestStatus, string> = {
  PENDING: "در انتظار",
  IN_PROGRESS: "در حال انجام",
  COMPLETED: "انجام‌شده",
  REJECTED: "ردشده",
};

export const itProcessTypeLabels: Record<ITProcessType, string> = {
  ACTIVE: "فعال",
  PASSIVE: "پایشی",
  PERIODIC_CHECK: "بازبینی دوره‌ای",
  PERIODIC_SERVICE: "سرویس دوره‌ای",
};

export const itFrequencyLabels: Record<ITProcessFrequency, string> = {
  NONE: "یک‌باره",
  DAILY: "روزانه",
  WEEKLY: "هفتگی",
  MONTHLY: "ماهانه",
  QUARTERLY: "فصلی",
  YEARLY: "سالانه",
};

export interface ITViewer {
  userId: number | null;
  role: AccessTokenPayload["role"] | null;
  isSupervisor: boolean;
  departmentCode: string | null;
}

export function getITViewer(): ITViewer {
  const payload = decodeAccessToken(getAccessToken() ?? "");
  return {
    userId: payload?.user_id ?? null,
    role: payload?.role ?? null,
    isSupervisor: payload?.is_supervisor === true,
    departmentCode: payload?.department_code ?? null,
  };
}

/** IsITStaff: IT operators and admins. */
export function isITStaff(viewer: ITViewer): boolean {
  return (
    viewer.role === "ADMIN" ||
    (viewer.role === "OPERATOR" && viewer.departmentCode === IT_DEPARTMENT_CODE)
  );
}

/** The IT supervisor — or an admin, who has the same authority here. */
export function isITSupervisor(viewer: ITViewer): boolean {
  return viewer.role === "ADMIN" || (isITStaff(viewer) && viewer.isSupervisor);
}

/** Marking a process done: its responsible person, or the IT supervisor. */
export function canMarkProcessDone(viewer: ITViewer, process: Pick<ITProcess, "responsible">): boolean {
  if (!isITStaff(viewer)) return false;
  return isITSupervisor(viewer) || (viewer.userId !== null && process.responsible === viewer.userId);
}
