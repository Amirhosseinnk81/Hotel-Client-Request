import { getAccessToken } from "@/lib/api/client";
import { decodeAccessToken } from "@/lib/api/tokens";
import type {
  AccessTokenPayload,
  ITGoalStatus,
  ITGoalType,
  ITPriority,
  ITProcess,
  ITProcessFrequency,
  ITProcessType,
  ITProjectStatus,
  ITRequestStatus,
  ITResource,
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

export const itProcessStatusLabels: Record<ITProcess["status"], string> = {
  ACTIVE: "فعال",
  PAUSED: "متوقف",
  ARCHIVED: "بایگانی",
};

export const itProjectStatusLabels: Record<ITProjectStatus, string> = {
  PLANNING: "برنامه‌ریزی",
  IN_PROGRESS: "در حال انجام",
  ON_HOLD: "معلق",
  DONE: "انجام‌شده",
  CANCELLED: "لغوشده",
};

export const itGoalStatusLabels: Record<ITGoalStatus, string> = {
  NOT_STARTED: "شروع‌نشده",
  IN_PROGRESS: "در حال انجام",
  ACHIEVED: "محقق‌شده",
  MISSED: "محقق‌نشده",
};

export const itGoalTypeLabels: Record<ITGoalType, string> = {
  SHORT_TERM: "کوتاه‌مدت",
  LONG_TERM: "بلندمدت",
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

// ---------------------------------------------------------------------------
// Create / edit rules per resource — the frontend side of CanWorkOnITItem.
// ---------------------------------------------------------------------------

/** The field that says whose item it is, per resource (null = supervisor-only). */
const ASSIGNEE_FIELD: Record<ITResource, "assigned_to" | null> = {
  tasks: "assigned_to",
  "department-requests": "assigned_to",
  // A process's responsible person may only "mark done" (its own button).
  processes: null,
  projects: null,
  goals: null,
};

/** Fields only the IT supervisor may change once an item exists. */
export const IT_SUPERVISOR_ONLY_FIELDS: Record<ITResource, readonly string[]> = {
  tasks: ["assigned_to", "priority"],
  "department-requests": ["assigned_to", "priority"],
  processes: [],
  projects: [],
  goals: [],
};

/** Regular IT operators may create their own tasks and log department requests. */
export function canCreateItItem(viewer: ITViewer, resource: ITResource): boolean {
  if (!isITStaff(viewer)) return false;
  if (isITSupervisor(viewer)) return true;
  return resource === "tasks" || resource === "department-requests";
}

export function canEditItItem(
  viewer: ITViewer,
  resource: ITResource,
  item: { assigned_to?: number | null }
): boolean {
  if (!isITStaff(viewer)) return false;
  if (isITSupervisor(viewer)) return true;
  const field = ASSIGNEE_FIELD[resource];
  return field !== null && viewer.userId !== null && item[field] === viewer.userId;
}

export function canDeleteItItem(viewer: ITViewer): boolean {
  return isITSupervisor(viewer);
}

/**
 * Whether a field is shown in the form. On create a regular operator may
 * set priority (like a guest's ticket) but never the assignee; on edit
 * neither — sending them at all is refused with 403.
 */
export function isItFieldEditable(
  viewer: ITViewer,
  resource: ITResource,
  field: string,
  mode: "create" | "edit"
): boolean {
  if (isITSupervisor(viewer)) return true;
  if (field === "assigned_to") return false;
  if (mode === "create") return true;
  return !IT_SUPERVISOR_ONLY_FIELDS[resource].includes(field);
}

/** Only the supervisor may turn a department's request down. */
export function itRequestStatusOptions(viewer: ITViewer): ITRequestStatus[] {
  const all: ITRequestStatus[] = ["PENDING", "IN_PROGRESS", "COMPLETED", "REJECTED"];
  return isITSupervisor(viewer) ? all : all.filter((status) => status !== "REJECTED");
}

/**
 * Only the fields that actually changed. A PATCH must never carry an
 * untouched supervisor-only field: the backend refuses the whole request
 * (403) on the field's mere presence, whatever its value.
 */
export function changedFields(
  original: Record<string, unknown>,
  values: Record<string, unknown>
): Record<string, unknown> {
  const diff: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(values)) {
    if ((original[key] ?? null) !== (value ?? null)) diff[key] = value;
  }
  return diff;
}

/** ISO timestamp -> value for <input type="datetime-local"> (local time). */
export function isoToLocalInput(iso: string | null): string {
  if (!iso) return "";
  const date = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(
    date.getHours()
  )}:${pad(date.getMinutes())}`;
}

/** <input type="datetime-local"> value -> ISO timestamp (or null when empty). */
export function localInputToIso(value: string): string | null {
  return value ? new Date(value).toISOString() : null;
}
