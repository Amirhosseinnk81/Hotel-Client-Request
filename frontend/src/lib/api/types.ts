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

export interface OperatorAvailability {
  is_available: boolean;
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