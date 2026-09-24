import { decodeAccessToken, isTokenExpired } from "./tokens";
import type {
  AdminStatsSummary,
  ApiErrorBody,
  AuthTokens,
  CannedResponse,
  Category,
  CreateTicketPayload,
  Department,
  DepartmentStatsSummary,
  GuestProfile,
  HotelInfo,
  CreateOutgoingITRequestPayload,
  ITProcess,
  ITResource,
  ITResourceMap,
  ITStaffMember,
  ITTodayDashboard,
  OutgoingITRequest,
  OperatorAvailability,
  OperatorColleague,
  QuickRequestTemplate,
  RefreshResponse,
  Ticket,
  TicketAttachment,
  TicketPriority,
  TicketStatus,
  TicketTimelineEntry,
  UpdateOperatorTicketPayload,
  UserRole,
} from "./types";

import { enqueue, findCachedTicket, isNetworkError, readThrough } from "@/lib/offline";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export class ApiError extends Error {
  status: number;
  errors?: ApiErrorBody["errors"];

  constructor(status: number, message: string, errors?: ApiErrorBody["errors"]) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.errors = errors;
  }
}

/**
 * The access token lives ONLY in memory (this module-level variable) —
 * never in localStorage, never in a JS-readable cookie. On a hard reload
 * it's gone and gets re-derived from the httpOnly refresh cookie via
 * restoreSession() (see AuthProvider). This bounds how long a stolen
 * token (e.g. via XSS) stays useful to its short lifetime, instead of
 * however long it happened to sit in localStorage.
 */
let currentAccessToken: string | null = null;

export function getAccessToken(): string | null {
  return currentAccessToken;
}

function setAccessToken(token: string | null): void {
  currentAccessToken = token;
  notifyTokensChanged(token ? { access: token, role: getRoleFromToken(token) } : null);
}

function getRoleFromToken(token: string): UserRole {
  return decodeAccessToken(token)?.role ?? "GUEST";
}

/**
 * Fired whenever the client changes the access token on its own (a silent
 * refresh, or a failed refresh clearing the session), so AuthContext can
 * sync its React state with what's now actually held in memory.
 */
type TokensListener = (tokens: AuthTokens | null) => void;
let tokensListener: TokensListener | null = null;

export function onTokensChanged(listener: TokensListener) {
  tokensListener = listener;
}

function notifyTokensChanged(tokens: AuthTokens | null) {
  tokensListener?.(tokens);
}

async function parseErrorBody(response: Response): Promise<ApiErrorBody> {
  try {
    const body = (await response.json()) as ApiErrorBody;
    if (body?.message) return body;
  } catch {
    // fall through to generic message below
  }
  return { success: false, message: `Request failed with status ${response.status}` };
}

/**
 * Raw refresh call — deliberately does not go through apiFetch (no auth
 * header, no retry loop). Sends no body: the refresh token travels only as
 * the httpOnly cookie the browser attaches automatically, which is why
 * `credentials: "include"` is required here.
 */
async function refreshAccessToken(): Promise<string> {
  const response = await fetch(`${API_URL}/auth/token/refresh/`, {
    method: "POST",
    credentials: "include",
  });

  if (!response.ok) {
    const body = await parseErrorBody(response);
    throw new ApiError(response.status, body.message, body.errors);
  }

  const data = (await response.json()) as RefreshResponse;
  setAccessToken(data.access);
  return data.access;
}

/**
 * The current access token, refreshed first if it has expired (or `force`
 * is set, e.g. after a 401). For callers that can't go through apiFetch —
 * the live event stream (lib/realtime.ts) reads a streaming body. Returns
 * the token for the Authorization header only; it is still kept nowhere
 * but the module variable above. Null means "not logged in any more".
 */
export async function getFreshAccessToken(force = false): Promise<string | null> {
  if (!force && currentAccessToken && !isTokenExpired(currentAccessToken)) {
    return currentAccessToken;
  }
  try {
    return await refreshAccessToken();
  } catch (err) {
    if (!isNetworkError(err)) setAccessToken(null);
    return null;
  }
}

/**
 * Called by AuthProvider on mount to silently restore a session from the
 * httpOnly refresh cookie (if any). Never throws — a missing/expired
 * cookie just means "not logged in", which is a normal, expected outcome,
 * not an error worth surfacing.
 *
 * "offline" means the server couldn't be reached at all, so we don't know
 * yet whether there is a session: the caller should wait for the network
 * rather than send the user to the login page (operator offline mode).
 */
export async function restoreSession(): Promise<AuthTokens | null | "offline"> {
  try {
    const access = await refreshAccessToken();
    return { access, role: getRoleFromToken(access) };
  } catch (err) {
    setAccessToken(null);
    return isNetworkError(err) ? "offline" : null;
  }
}

interface ApiFetchOptions extends RequestInit {
  /** Skip attaching an Authorization header (for login endpoints, etc). */
  skipAuth?: boolean;
}

export async function apiFetch<T>(path: string, options: ApiFetchOptions = {}): Promise<T> {
  const { skipAuth = false, headers, ...rest } = options;

  let token = currentAccessToken;

  if (!skipAuth && token && isTokenExpired(token)) {
    try {
      token = await refreshAccessToken();
    } catch {
      setAccessToken(null);
      token = null;
    }
  }

  const requestHeaders = new Headers(headers);
  // FormData (file uploads) must NOT get an explicit Content-Type — the
  // browser sets it itself, including the multipart boundary. Setting it
  // manually here would silently break every attachment upload.
  if (!(rest.body instanceof FormData)) {
    requestHeaders.set("Content-Type", "application/json");
  }
  if (!skipAuth && token) {
    requestHeaders.set("Authorization", `Bearer ${token}`);
  }

  let response = await fetch(`${API_URL}${path}`, { ...rest, headers: requestHeaders });

  // One retry after a silent refresh, in case the token expired mid-flight
  // (clock skew, a long-running request, etc).
  if (response.status === 401 && !skipAuth && token) {
    try {
      const refreshed = await refreshAccessToken();
      requestHeaders.set("Authorization", `Bearer ${refreshed}`);
      response = await fetch(`${API_URL}${path}`, { ...rest, headers: requestHeaders });
    } catch {
      setAccessToken(null);
    }
  }

  if (!response.ok) {
    const body = await parseErrorBody(response);
    throw new ApiError(response.status, body.message, body.errors);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

// ---------------------------------------------------------------------------
// Auth endpoints — these deliberately skip auth (no token exists yet).
// ---------------------------------------------------------------------------

export async function loginGuest(nationalId: string, roomNumber: string): Promise<AuthTokens> {
  const response = await fetch(`${API_URL}/auth/guest/login/`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ national_id: nationalId, room_number: roomNumber }),
  });

  if (!response.ok) {
    const body = await parseErrorBody(response);
    throw new ApiError(response.status, body.message, body.errors);
  }

  const data = (await response.json()) as AuthTokens;
  setAccessToken(data.access);
  return data;
}

export async function loginOperator(username: string, password: string): Promise<AuthTokens> {
  const response = await fetch(`${API_URL}/auth/operator/login/`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });

  if (!response.ok) {
    const body = await parseErrorBody(response);
    throw new ApiError(response.status, body.message, body.errors);
  }

  const data = (await response.json()) as AuthTokens;
  setAccessToken(data.access);
  return data;
}

/** Blacklists the refresh cookie server-side and clears it, then drops the in-memory access token. */
export async function logout(): Promise<void> {
  try {
    await fetch(`${API_URL}/auth/logout/`, {
      method: "POST",
      credentials: "include",
    });
  } finally {
    // Always clear the local session, even if the network call failed
    // (offline, server hiccup, etc) — the user still expects to be logged
    // out of this tab.
    setAccessToken(null);
  }
}

export function getCurrentRole(): UserRole | null {
  return currentAccessToken ? getRoleFromToken(currentAccessToken) : null;
}

// ---------------------------------------------------------------------------
// Guest endpoints
// ---------------------------------------------------------------------------

export async function getGuestProfile(): Promise<GuestProfile> {
  return apiFetch<GuestProfile>("/guest/profile/");
}

// ---------------------------------------------------------------------------
// Reference data (read for any authenticated role)
// ---------------------------------------------------------------------------

interface PaginatedResponse<T> {
  results?: T[];
  count?: number;
  next?: string | null;
  previous?: string | null;
}

/**
 * Follows DRF's `next` link across every page and returns the full,
 * combined list. Without this, any list beyond the backend's default page
 * size would silently lose items past the first page.
 */
async function getAllPages<T>(path: string): Promise<T[]> {
  const results: T[] = [];
  let nextPath: string | null = path;

  while (nextPath) {
    const data: T[] | PaginatedResponse<T> = await apiFetch<T[] | PaginatedResponse<T>>(nextPath);

    if (Array.isArray(data)) {
      results.push(...data);
      break;
    }

    results.push(...(data.results ?? []));

    if (data.next) {
      // `next` comes back as an absolute URL (e.g.
      // http://127.0.0.1:8000/api/v1/tickets/?page=2); apiFetch expects a
      // path relative to API_URL, so strip the origin and /api/v1 prefix.
      const nextUrl: URL = new URL(data.next);
      nextPath = nextUrl.pathname.replace(/^\/api\/v1/, "") + nextUrl.search;
    } else {
      nextPath = null;
    }
  }

  return results;
}

export async function getDepartments(): Promise<Department[]> {
  return getAllPages<Department>("/departments/");
}

export async function getCategories(): Promise<Category[]> {
  return getAllPages<Category>("/categories/");
}

// ---------------------------------------------------------------------------
// Tickets (guest side)
// ---------------------------------------------------------------------------

export async function createTicket(payload: CreateTicketPayload): Promise<Ticket> {
  return apiFetch<Ticket>("/tickets/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getTickets(search?: string): Promise<Ticket[]> {
  const query = new URLSearchParams();
  if (search) query.set("search", search);
  const qs = query.toString();

  return getAllPages<Ticket>(`/tickets/${qs ? `?${qs}` : ""}`);
}

export async function getTicketDetail(id: number | string): Promise<Ticket> {
  return apiFetch<Ticket>(`/tickets/${id}/`);
}

/** Stage 2.3 — rate a RESOLVED ticket, once. */
export async function rateTicket(
  id: number | string,
  rating: number,
  feedback?: string
): Promise<Ticket> {
  return apiFetch<Ticket>(`/tickets/${id}/rate/`, {
    method: "POST",
    body: JSON.stringify({ rating, feedback: feedback ?? "" }),
  });
}

/** Stage 2.3 — reopen a RESOLVED ticket (within 48h, once ever — see Ticket.can_reopen). */
export async function reopenTicket(id: number | string): Promise<Ticket> {
  return apiFetch<Ticket>(`/tickets/${id}/reopen/`, { method: "POST" });
}

/** Stage 2.3 — one-click shortcuts for common requests, shown on the new-ticket form. */
export async function getQuickTemplates(): Promise<QuickRequestTemplate[]> {
  return apiFetch<QuickRequestTemplate[]>("/quick-templates/");
}

// ---------------------------------------------------------------------------
// Tickets (operator side)
// ---------------------------------------------------------------------------

export interface OperatorTicketFilters {
  status?: TicketStatus;
  priority?: TicketPriority;
  search?: string;
}

// ---------------------------------------------------------------------------
// Operator offline mode (lib/offline.ts): the reads below fall back to their
// last good answer when the network is down; a status change or a note made
// while offline is queued instead of lost.
// ---------------------------------------------------------------------------

/**
 * Thrown instead of a network error when the change was queued for later.
 * `ticket` is what the ticket will look like once it is sent, so the page
 * can show it right away. Check for it before the generic error handling.
 */
export class QueuedOfflineError extends ApiError {
  ticket?: Ticket;

  constructor(ticket?: Ticket) {
    super(0, "آفلاین هستید؛ این تغییر در صف ماند و با وصل‌شدن اینترنت ارسال می‌شود.");
    this.name = "QueuedOfflineError";
    this.ticket = ticket;
  }
}

/** The logged-in user's id, from the in-memory token — scopes the offline queue. */
export function getCurrentUserId(): number | null {
  return decodeAccessToken(currentAccessToken ?? "")?.user_id ?? null;
}

const QUEUEABLE_FIELDS = new Set(["status", "resolution"]);

/**
 * Straight to the server — no cache fallback, no queueing. For replaying
 * the offline queue (lib/offline.ts flushQueue): a replay that fails must
 * report the failure, not quietly queue itself again or read a stale copy.
 */
export const directOperatorApi = {
  getTicket: (id: number) => apiFetch<Ticket>(`/operator/tickets/${id}/`),
  updateTicket: (id: number, payload: UpdateOperatorTicketPayload) =>
    apiFetch<Ticket>(`/operator/tickets/${id}/`, { method: "PATCH", body: JSON.stringify(payload) }),
  addNote: (id: number, text: string) =>
    apiFetch<TicketTimelineEntry>(`/operator/tickets/${id}/notes/`, {
      method: "POST",
      body: JSON.stringify({ text }),
    }),
};

export async function getOperatorTickets(
  filters: OperatorTicketFilters = {}
): Promise<Ticket[]> {
  const query = new URLSearchParams();
  if (filters.status) query.set("status", filters.status);
  if (filters.priority) query.set("priority", filters.priority);
  if (filters.search) query.set("search", filters.search);
  const qs = query.toString();

  return readThrough(`operator/tickets?${qs}`, () =>
    getAllPages<Ticket>(`/operator/tickets/${qs ? `?${qs}` : ""}`)
  );
}

export async function getOperatorTicketDetail(id: number | string): Promise<Ticket> {
  return readThrough(`operator/tickets/${id}`, () => apiFetch<Ticket>(`/operator/tickets/${id}/`));
}

/**
 * PATCH an operator ticket. Offline, a pure status/resolution change is
 * queued (throws QueuedOfflineError with the expected ticket); anything
 * else — assignment, priority — needs the network and fails as usual.
 */
export async function updateOperatorTicket(
  id: number | string,
  payload: UpdateOperatorTicketPayload
): Promise<Ticket> {
  try {
    return await apiFetch<Ticket>(`/operator/tickets/${id}/`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  } catch (err) {
    const queueable = Object.keys(payload).every((field) => QUEUEABLE_FIELDS.has(field));
    const base = isNetworkError(err) && queueable ? findCachedTicket(Number(id)) : null;
    if (!base) throw err;

    enqueue(getCurrentUserId(), {
      kind: "status",
      ticketId: base.id,
      ticketTitle: base.title,
      payload: { status: payload.status, resolution: payload.resolution },
      baseUpdatedAt: base.updated_at,
    });
    throw new QueuedOfflineError({ ...base, ...payload } as Ticket);
  }
}

export async function assignTicketToSelf(id: number | string): Promise<Ticket> {
  return apiFetch<Ticket>(`/operator/tickets/${id}/assign/`, {
    method: "POST",
  });
}

export async function getOperatorColleagues(): Promise<OperatorColleague[]> {
  return readThrough("operator/colleagues", () =>
    apiFetch<OperatorColleague[]>("/operator/colleagues/")
  );
}

/** Merged, chronologically-sorted history + notes timeline for a ticket. */
export async function getOperatorTicketHistory(
  id: number | string
): Promise<TicketTimelineEntry[]> {
  return readThrough(`operator/tickets/${id}/history`, () =>
    apiFetch<TicketTimelineEntry[]>(`/operator/tickets/${id}/history/`)
  );
}

export async function addOperatorTicketNote(
  id: number | string,
  text: string
): Promise<TicketTimelineEntry> {
  try {
    return await apiFetch<TicketTimelineEntry>(`/operator/tickets/${id}/notes/`, {
      method: "POST",
      body: JSON.stringify({ text }),
    });
  } catch (err) {
    // A note is append-only, so it can't conflict with anyone — queue it.
    if (!isNetworkError(err)) throw err;
    const base = findCachedTicket(Number(id));
    enqueue(getCurrentUserId(), {
      kind: "note",
      ticketId: Number(id),
      ticketTitle: base?.title ?? `#${id}`,
      text,
    });
    throw new QueuedOfflineError(base ?? undefined);
  }
}

/** Guest attaches a photo to their own ticket — at creation or later, any status. */
export async function addGuestTicketAttachment(
  ticketId: number | string,
  file: File
): Promise<TicketAttachment> {
  const formData = new FormData();
  formData.append("image", file);
  return apiFetch<TicketAttachment>(`/tickets/${ticketId}/attachments/`, {
    method: "POST",
    body: formData,
  });
}

/** Operator attaches a "proof of fix" photo — only the assigned operator may. */
export async function addOperatorTicketAttachment(
  ticketId: number | string,
  file: File
): Promise<TicketAttachment> {
  const formData = new FormData();
  formData.append("image", file);
  return apiFetch<TicketAttachment>(`/operator/tickets/${ticketId}/attachments/`, {
    method: "POST",
    body: formData,
  });
}

/**
 * The logged-in operator's own available/busy status. Read-only: it's
 * derived on the server from their assigned tickets (busy until every
 * one is RESOLVED or CANCELLED), so there is nothing to set.
 */
export async function getMyOperatorStatus(): Promise<OperatorAvailability> {
  return readThrough("operator/me/status", () =>
    apiFetch<OperatorAvailability>("/operator/me/status/")
  );
}

/** Ready-made texts for notes and resolutions: own department's plus hotel-wide ones. */
export async function getCannedResponses(): Promise<CannedResponse[]> {
  return readThrough("operator/canned-responses", () =>
    apiFetch<CannedResponse[]>("/operator/canned-responses/")
  );
}

/** Other open tickets of the same guest in the department — likely duplicates. */
export async function getMergeCandidates(id: number | string): Promise<Ticket[]> {
  return apiFetch<Ticket[]>(`/operator/tickets/${id}/merge-candidates/`);
}

/** Supervisor only: fold duplicate `id` into ticket `into`. Returns the kept ticket. */
export async function mergeTicket(id: number | string, into: number): Promise<Ticket> {
  return apiFetch<Ticket>(`/operator/tickets/${id}/merge/`, {
    method: "POST",
    body: JSON.stringify({ into }),
  });
}

/** The guest help page: Wi-Fi, breakfast hours, check-out time... */
export async function getHotelInfo(): Promise<HotelInfo[]> {
  return apiFetch<HotelInfo[]>("/guest/hotel-info/");
}

/** Count of currently-overdue tickets in the operator's department (Stage 2.9). */
export async function getOverdueTicketCount(): Promise<number> {
  const { count } = await apiFetch<{ count: number }>("/operator/tickets/overdue-count/");
  return count;
}

/** The whole hotel — admins only. Same numbers as the Django Admin Stats Summary page. */
export async function getAdminStatsSummary(): Promise<AdminStatsSummary> {
  return apiFetch<AdminStatsSummary>("/admin/stats/summary/");
}

/** The caller's own department — any operator, regular or supervisor. */
export async function getDepartmentStatsSummary(): Promise<DepartmentStatsSummary> {
  return apiFetch<DepartmentStatsSummary>("/operator/stats/summary/");
}

/** IT Ops — today's due work, open requests and live occupancy (IT staff and admins). */
export async function getItOpsToday(): Promise<ITTodayDashboard> {
  return apiFetch<ITTodayDashboard>("/it-ops/today/");
}

/**
 * Marks a process as carried out now. The server moves next_due_at one
 * period on for a recurring process; only its responsible person or the
 * IT supervisor may do this.
 */
export async function markItProcessDone(processId: number): Promise<ITProcess> {
  return apiFetch<ITProcess>(`/it-ops/processes/${processId}/mark-done/`, { method: "POST" });
}

/** Every row of one IT Ops resource (all pages). */
export async function listItItems<R extends ITResource>(resource: R): Promise<ITResourceMap[R][]> {
  return getAllPages<ITResourceMap[R]>(`/it-ops/${resource}/`);
}

export async function createItItem<R extends ITResource>(
  resource: R,
  payload: Record<string, unknown>
): Promise<ITResourceMap[R]> {
  return apiFetch<ITResourceMap[R]>(`/it-ops/${resource}/`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateItItem<R extends ITResource>(
  resource: R,
  id: number,
  payload: Record<string, unknown>
): Promise<ITResourceMap[R]> {
  return apiFetch<ITResourceMap[R]>(`/it-ops/${resource}/${id}/`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function deleteItItem(resource: ITResource, id: number): Promise<void> {
  await apiFetch<void>(`/it-ops/${resource}/${id}/`, { method: "DELETE" });
}

/** IT operators, for the assignee dropdowns (IT staff only). */
export async function getItStaff(): Promise<ITStaffMember[]> {
  return apiFetch<ITStaffMember[]>("/it-ops/staff/");
}

/** The caller's own department's requests to IT (any operator with a department). */
export async function getOutgoingItRequests(): Promise<OutgoingITRequest[]> {
  return getAllPages<OutgoingITRequest>("/it-ops/outgoing-requests/");
}

export async function createOutgoingItRequest(
  payload: CreateOutgoingITRequestPayload
): Promise<OutgoingITRequest> {
  return apiFetch<OutgoingITRequest>("/it-ops/outgoing-requests/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/**
 * Stage 2.7 — PDF export. Doesn't go through apiFetch since that always
 * parses the response as JSON; this mirrors apiFetch's auth-header +
 * one-retry-on-401 logic but returns the raw PDF bytes as a Blob
 * instead. Works for guests (own ticket), operators (own department),
 * and admins — the backend enforces exactly who's allowed.
 */
export async function exportTicketPdf(ticketId: number | string): Promise<Blob> {
  let token = currentAccessToken;
  if (token && isTokenExpired(token)) {
    try {
      token = await refreshAccessToken();
    } catch {
      setAccessToken(null);
      token = null;
    }
  }

  const headers = new Headers();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  let response = await fetch(`${API_URL}/tickets/${ticketId}/export/pdf/`, { headers });

  if (response.status === 401 && token) {
    try {
      const refreshed = await refreshAccessToken();
      headers.set("Authorization", `Bearer ${refreshed}`);
      response = await fetch(`${API_URL}/tickets/${ticketId}/export/pdf/`, { headers });
    } catch {
      setAccessToken(null);
    }
  }

  if (!response.ok) {
    const body = await parseErrorBody(response);
    throw new ApiError(response.status, body.message, body.errors);
  }

  return response.blob();
}