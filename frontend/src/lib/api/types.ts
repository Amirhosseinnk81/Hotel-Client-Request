/**
 * Shared types for talking to the Django backend.
 *
 * The backend wraps every error response in a consistent envelope
 * (see apps/core/exceptions.py on the backend):
 *
 *   { "success": false, "message": "...", "errors": { ... } }
 */

export type UserRole = "GUEST" | "OPERATOR" | "ADMIN";

export interface AuthTokens {
  access: string;
  role: UserRole;
}

export interface RefreshResponse {
  access: string;
}

export interface ApiErrorBody {
  success: false;
  message: string;
  errors?: Record<string, string[] | string>;
}

/** Decoded shape of the access token's payload (custom claims only). */
export interface AccessTokenPayload {
  role: UserRole;
  exp: number;
  user_id: number;
  /** Only present on operator/admin tokens — guest tokens don't carry this claim. */
  username?: string;
  /**
   * Operator/admin tokens only. A UI hint for which controls to show,
   * never an authorization decision: the backend re-reads is_supervisor
   * from the database on every request, and this claim can lag behind a
   * promotion or demotion until the operator next logs in.
   */
  is_supervisor?: boolean;
  /**
   * Operator/admin tokens only; null for an account without a department.
   * Same kind of UI hint as is_supervisor: it decides whether the IT Ops
   * link is shown, while the backend (IsITStaff) re-reads the department
   * from the database on every request.
   */
  department_code?: string | null;
}

export interface GuestProfile {
  id: number;
  full_name: string;
  national_id: string;
  phone: string;
  room_number: string | null;
}

export interface Department {
  id: number;
  name: string;
  code: string;
  is_active: boolean;
}

export interface Category {
  id: number;
  name: string;
  code: string;
  is_active: boolean;
  /** Expected response time in minutes for tickets in this category (Stage 2.9). */
  sla_minutes: number;
}

export type TicketStatus = "OPEN" | "IN_PROGRESS" | "RESOLVED" | "CANCELLED";
export type TicketPriority = "LOW" | "NORMAL" | "HIGH" | "URGENT";

export interface TicketAttachment {
  id: number;
  image: string;
  uploaded_by_username: string | null;
  created_at: string;
}

export interface Ticket {
  id: number;
  title: string;
  description: string;
  status: TicketStatus;
  priority: TicketPriority;
  department: number;
  department_name: string;
  category: number;
  category_name: string;
  room_number: string;
  resolution: string | null;
  /** Present on tickets returned by operator endpoints; absent on guest-facing reads. */
  assigned_to?: number | null;
  assigned_to_username?: string | null;
  /** Operator endpoints only (Stage 2.9) — past category.sla_minutes and still OPEN/IN_PROGRESS. */
  is_overdue?: boolean;
  overdue_since?: string | null;
  /** Guest-facing fields (Stage 2.3). */
  guest_rating?: number | null;
  guest_feedback?: string;
  reopened_at?: string | null;
  can_reopen?: boolean;
  /** Stage 2.8 — present on both guest and operator ticket reads. */
  attachments: TicketAttachment[];
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
}

export interface QuickRequestTemplate {
  id: number;
  title: string;
  /** lucide-react icon name. */
  icon: string;
  department: number;
  category: number;
  order: number;
}

export interface CreateTicketPayload {
  title: string;
  description: string;
  department: number;
  category: number;
  priority: TicketPriority;
}

export interface UpdateOperatorTicketPayload {
  status?: TicketStatus;
  priority?: TicketPriority;
  resolution?: string;
  assigned_to?: number | null;
}

export interface OperatorColleague {
  id: number;
  username: string;
  /** Assigned tickets still OPEN or IN_PROGRESS in this department. */
  active_tickets: number;
  /** Derived on the server: true only while active_tickets is 0. */
  is_available: boolean;
}

export type TicketHistoryAction =
  | "CREATED"
  | "UPDATED"
  | "ASSIGNED"
  | "STATUS_CHANGED"
  | "PRIORITY_CHANGED";

export interface TicketHistoryEntry {
  entry_type: "history";
  id: number;
  action: TicketHistoryAction;
  action_display: string;
  old_value: string | null;
  new_value: string | null;
  user_username: string | null;
  created_at: string;
}

export interface TicketNoteEntry {
  entry_type: "note";
  id: number;
  text: string;
  author_username: string | null;
  created_at: string;
}

/** A single row in the merged ticket timeline, already sorted chronologically by the backend. */
export type TicketTimelineEntry = TicketHistoryEntry | TicketNoteEntry;

/**
 * GET /operator/me/status/ — the logged-in operator's own status. Derived
 * on the server from their assignments (busy until every assigned ticket
 * is RESOLVED or CANCELLED); there is no way to set it by hand.
 */
export interface OperatorAvailability {
  is_available: boolean;
  active_tickets: number;
}

/** Ticket count per status — every status always present (0, never missing). */
export type StatsByStatus = Record<TicketStatus, number>;

/** GET /admin/stats/summary/ — the whole hotel, admins only. */
export interface AdminStatsSummary {
  by_status: StatsByStatus;
  by_department: {
    department_id: number;
    department_name: string;
    open: number;
    in_progress: number;
    resolved: number;
    cancelled: number;
    total: number;
  }[];
  avg_resolution_minutes: number | null;
  overdue_count: number;
  resolution_window_days: number;
  generated_at: string;
}

/** One operator's workload in a department summary. */
export interface DepartmentOperatorLoad {
  operator_id: number;
  username: string;
  is_supervisor: boolean;
  /** Assigned tickets still OPEN or IN_PROGRESS. */
  active: number;
  /** Assigned tickets resolved within resolution_window_days. */
  resolved_recent: number;
}

/** GET /operator/stats/summary/ — the caller's own department. */
export interface DepartmentStatsSummary {
  department_id: number;
  department_name: string;
  by_status: StatsByStatus;
  by_operator: DepartmentOperatorLoad[];
  avg_resolution_minutes: number | null;
  overdue_count: number;
  resolution_window_days: number;
  generated_at: string;
}

// ---------------------------------------------------------------------------
// IT Ops (/it-ops/) — see apps/it_ops on the backend.
// ---------------------------------------------------------------------------

export type ITPriority = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type ITTaskStatus = "TODO" | "IN_PROGRESS" | "DONE" | "BLOCKED";
export type ITRequestStatus = "PENDING" | "IN_PROGRESS" | "COMPLETED" | "REJECTED";
export type ITProcessType = "ACTIVE" | "PASSIVE" | "PERIODIC_CHECK" | "PERIODIC_SERVICE";
export type ITProcessFrequency = "NONE" | "DAILY" | "WEEKLY" | "MONTHLY" | "QUARTERLY" | "YEARLY";

export interface ITTask {
  id: number;
  title: string;
  description: string;
  status: ITTaskStatus;
  priority: ITPriority;
  assigned_to: number | null;
  assigned_to_username: string | null;
  assigned_by: number | null;
  assigned_by_username: string | null;
  due_date: string | null;
  related_process: number | null;
  related_project: number | null;
  related_request: number | null;
  created_at: string;
  updated_at: string;
}

export interface ITProcess {
  id: number;
  title: string;
  description: string;
  process_type: ITProcessType;
  department: number | null;
  department_name: string | null;
  frequency: ITProcessFrequency;
  status: "ACTIVE" | "PAUSED" | "ARCHIVED";
  responsible: number | null;
  responsible_username: string | null;
  last_done_at: string | null;
  /** Calculated on the server for recurring processes (Process.save()). */
  next_due_at: string | null;
  is_overdue: boolean;
  created_at: string;
  updated_at: string;
}

export interface ITDepartmentRequest {
  id: number;
  title: string;
  description: string;
  requesting_department: number | null;
  requesting_department_name: string | null;
  requested_by_name: string;
  priority: ITPriority;
  status: ITRequestStatus;
  assigned_to: number | null;
  assigned_to_username: string | null;
  resolved_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ITRoomStatsToday {
  date: string;
  total_rooms: number;
  occupied_rooms: number;
  vacant_rooms: number;
  out_of_order_rooms: number;
  occupancy_rate: number;
}

/** GET /it-ops/today/ */
export interface ITTodayDashboard {
  date: string;
  generated_at: string;
  tasks_due_or_overdue: ITTask[];
  processes_due_or_overdue: ITProcess[];
  open_department_requests: ITDepartmentRequest[];
  room_stats_today: ITRoomStatsToday;
  my_open_tasks_count: number;
}
