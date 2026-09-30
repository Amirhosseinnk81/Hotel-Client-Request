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
  /** First-response target in minutes (someone starts on it); capped at sla_minutes. */
  response_sla_minutes: number;
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
  /**
   * Operator endpoints only — the first-response half of the SLA: when
   * someone first started on it (moved it to IN_PROGRESS), the deadline for
   * that, and whether it is still waiting past it.
   */
  first_response_at?: string | null;
  response_deadline?: string;
  is_response_overdue?: boolean;
  /** Guest-facing fields (Stage 2.3). */
  guest_rating?: number | null;
  guest_feedback?: string;
  reopened_at?: string | null;
  can_reopen?: boolean;
  /** Set when a supervisor merged this duplicate into another ticket (it is then CANCELLED). */
  merged_into?: number | null;
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
  | "PRIORITY_CHANGED"
  | "MERGED";

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
    rating_avg: number | null;
    rating_count: number;
  }[];
  avg_resolution_minutes: number | null;
  overdue_count: number;
  /** Still waiting for anyone to start on them, past their first-response target (right now). */
  response_overdue_count: number;
  /** Over the resolution window. Null when there was nothing to measure. */
  avg_first_response_minutes: number | null;
  response_sla_met_percent: number | null;
  resolution_sla_met_percent: number | null;
  /** Guest ratings (1-5) over the window; null average when there were none. */
  rating_avg: number | null;
  rating_count: number;
  /** Ratings per star, keys "1".."5". */
  rating_distribution: Record<"1" | "2" | "3" | "4" | "5", number>;
  recent_feedback: RecentFeedback[];
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
  rating_avg: number | null;
  rating_count: number;
}

/** One recent written guest comment (ratings report). */
export interface RecentFeedback {
  ticket_id: number;
  title: string;
  rating: number;
  feedback: string;
  operator: string | null;
  department_name: string;
  resolved_at: string;
}

/** GET /operator/stats/summary/ — the caller's own department. */
export interface DepartmentStatsSummary {
  department_id: number;
  department_name: string;
  by_status: StatsByStatus;
  by_operator: DepartmentOperatorLoad[];
  avg_resolution_minutes: number | null;
  overdue_count: number;
  /** Still waiting for anyone to start on them, past their first-response target (right now). */
  response_overdue_count: number;
  /** Over the resolution window. Null when there was nothing to measure. */
  avg_first_response_minutes: number | null;
  response_sla_met_percent: number | null;
  resolution_sla_met_percent: number | null;
  /** Guest ratings (1-5) over the window; null average when there were none. */
  rating_avg: number | null;
  rating_count: number;
  /** Ratings per star, keys "1".."5". */
  rating_distribution: Record<"1" | "2" | "3" | "4" | "5", number>;
  recent_feedback: RecentFeedback[];
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
  /** Set when a department filed it from its own panel (outgoing-requests). */
  requested_by: number | null;
  requested_by_username: string | null;
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

export type ITProjectStatus = "PLANNING" | "IN_PROGRESS" | "ON_HOLD" | "DONE" | "CANCELLED";
export type ITGoalStatus = "NOT_STARTED" | "IN_PROGRESS" | "ACHIEVED" | "MISSED";
export type ITGoalType = "SHORT_TERM" | "LONG_TERM";

export interface ITProject {
  id: number;
  title: string;
  description: string;
  status: ITProjectStatus;
  priority: ITPriority;
  owner: number | null;
  owner_username: string | null;
  start_date: string | null;
  due_date: string | null;
  created_at: string;
  updated_at: string;
}

export interface ITGoal {
  id: number;
  title: string;
  description: string;
  goal_type: ITGoalType;
  status: ITGoalStatus;
  target_date: string | null;
  owner: number | null;
  owner_username: string | null;
  related_project: number | null;
  related_project_title: string | null;
  created_at: string;
  updated_at: string;
}

/** GET /it-ops/staff/ — an IT operator, for assignee dropdowns. */
export interface ITStaffMember {
  id: number;
  username: string;
  is_supervisor: boolean;
}

/**
 * /it-ops/outgoing-requests/ — a department's own request to IT, as that
 * department sees it. Only title/description/priority are writable.
 */
/** A photo on a request to IT — the socket, the error on screen, a model number. */
export interface ITRequestAttachment {
  id: number;
  /** Absolute URL of the uploaded image. */
  image: string;
  uploaded_by_username: string | null;
  created_at: string;
}

/**
 * GET /it-ops/request-templates/ — a one-click shortcut on the "ask IT"
 * form. Picking one fills the title, the description and the urgency.
 */
export interface ITRequestTemplate {
  id: number;
  title: string;
  description: string;
  /** lucide-react icon name; an unknown one falls back to a generic icon. */
  icon: string;
  priority: ITPriority;
  order: number;
}

export interface OutgoingITRequest {
  id: number;
  title: string;
  description: string;
  priority: ITPriority;
  status: ITRequestStatus;
  requesting_department_name: string | null;
  requested_by_username: string | null;
  assigned_to_username: string | null;
  attachments: ITRequestAttachment[];
  /** 1-5, given once by the asking department after the work is completed. */
  rating: number | null;
  feedback: string;
  rated_at: string | null;
  /** Whether the "how did it go?" box should be offered — decided by the server. */
  can_be_rated: boolean;
  resolved_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface CreateOutgoingITRequestPayload {
  title: string;
  description?: string;
  priority?: ITPriority;
}

/** The IT Ops resources with full CRUD, by URL segment. */
export interface ITResourceMap {
  tasks: ITTask;
  "department-requests": ITDepartmentRequest;
  processes: ITProcess;
  projects: ITProject;
  goals: ITGoal;
}
export type ITResource = keyof ITResourceMap;

/** GET /operator/canned-responses/ — a ready-made text for notes and resolutions. */
export interface CannedResponse {
  id: number;
  title: string;
  body: string;
  /** Null = offered to every department. */
  department: number | null;
}

/** GET /guest/hotel-info/ — one entry of the guest help page. English fields may be empty. */
export interface HotelInfo {
  id: number;
  title: string;
  body: string;
  title_en: string;
  body_en: string;
  /** lucide-react icon name. */
  icon: string;
}

/**
 * GET /extensions/ — one line of the hotel's internal phone directory
 * (apps/extensions, ported from the separate Flask app). Staff read it;
 * only admins change it, in Django Admin.
 */
export interface Extension {
  id: number;
  extension: string;
  title: string;
  person_name: string;
  /** The real department's id, or null for a number that belongs to none. */
  department: number | null;
  department_name: string;
  /** Free text, e.g. «۰۸:۰۰ تا ۲۰:۰۰» — so the caller knows if anyone is there. */
  department_working_hours: string;
  location: string;
  email: string;
  mobile: string;
  notes: string;
  /** False for a number that exists but is out of use. */
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

/**
 * GET /guest/news/ and /operator/news/ — a hotel announcement or event
 * (apps/news). Written in Django Admin; read-only here. The English
 * fields are optional and fall back to the Persian ones, like HotelInfo.
 */
export interface NewsItem {
  id: number;
  title: string;
  body: string;
  title_en: string;
  body_en: string;
  kind: "NEWS" | "EVENT";
  audience: "GUEST" | "STAFF" | "BOTH";
  /** Staff items only: null means the whole hotel. */
  department: number | null;
  department_name: string;
  /** When the event happens — separate from the publish window. */
  event_at: string | null;
  location: string;
  is_pinned: boolean;
  publish_at: string;
  expires_at: string | null;
  /** lucide-react icon name. */
  icon: string;
}

/** GET /chat/conversations/ — one thread in my chat inbox (apps/chat). */
export interface Conversation {
  id: number;
  kind: "GUEST" | "STAFF";
  title: string;
  subject: string;
  guest_name: string;
  room_number: string;
  department: number | null;
  department_name: string;
  /** «اپراتور رضا» for everyone in the thread. */
  participant_labels: string[];
  unread: number;
  last_message: string;
  last_message_at: string | null;
  is_closed: boolean;
  created_at: string;
}

/**
 * One chat message. `sender_label` is always «اپراتور رضا» / «مهمان …» /
 * «سیستم» — a guest must never see an anonymous bubble and wonder
 * whether there is a person on the other end.
 */
export interface ChatMessage {
  id: number;
  conversation: number;
  body: string;
  sender: number | null;
  sender_name: string;
  sender_role: "GUEST" | "OPERATOR" | "ADMIN" | null;
  sender_label: string;
  created_at: string;
}

/**
 * GET /chat/config/ — which transport is live. The panel asks rather
 * than being built for one, so switching the hotel from the SSE stream
 * to real WebSockets is a server setting, not a frontend release.
 */
export interface ChatConfig {
  transport: "sse" | "websocket";
  /** Empty on SSE. */
  websocket_path: string;
  poll_seconds: number;
}
