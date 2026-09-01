import { decodeAccessToken, isTokenExpired } from "./tokens";
import type {
  ApiErrorBody,
  AuthTokens,
  Category,
  CreateTicketPayload,
  Department,
  GuestProfile,
  OperatorAvailability,
  OperatorColleague,
  QuickRequestTemplate,
  RefreshResponse,
  Ticket,
  TicketPriority,
  TicketStatus,
  TicketTimelineEntry,
  UpdateOperatorTicketPayload,
  UserRole,
} from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

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
 * Called once by AuthProvider on mount to silently restore a session from
 * the httpOnly refresh cookie (if any). Never throws — a missing/expired
 * cookie just means "not logged in", which is a normal, expected outcome,
 * not an error worth surfacing.
 */
export async function restoreSession(): Promise<AuthTokens | null> {
  try {
    const access = await refreshAccessToken();
    return { access, role: getRoleFromToken(access) };
  } catch {
    setAccessToken(null);
    return null;
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
  requestHeaders.set("Content-Type", "application/json");
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

export async function getOperatorTickets(
  filters: OperatorTicketFilters = {}
): Promise<Ticket[]> {
  const query = new URLSearchParams();
  if (filters.status) query.set("status", filters.status);
  if (filters.priority) query.set("priority", filters.priority);
  if (filters.search) query.set("search", filters.search);
  const qs = query.toString();

  return getAllPages<Ticket>(`/operator/tickets/${qs ? `?${qs}` : ""}`);
}

export async function getOperatorTicketDetail(id: number | string): Promise<Ticket> {
  return apiFetch<Ticket>(`/operator/tickets/${id}/`);
}

export async function updateOperatorTicket(
  id: number | string,
  payload: UpdateOperatorTicketPayload
): Promise<Ticket> {
  return apiFetch<Ticket>(`/operator/tickets/${id}/`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function assignTicketToSelf(id: number | string): Promise<Ticket> {
  return apiFetch<Ticket>(`/operator/tickets/${id}/assign/`, {
    method: "POST",
  });
}

export async function getOperatorColleagues(): Promise<OperatorColleague[]> {
  return apiFetch<OperatorColleague[]>("/operator/colleagues/");
}

/** Merged, chronologically-sorted history + notes timeline for a ticket. */
export async function getOperatorTicketHistory(
  id: number | string
): Promise<TicketTimelineEntry[]> {
  return apiFetch<TicketTimelineEntry[]>(`/operator/tickets/${id}/history/`);
}

export async function addOperatorTicketNote(
  id: number | string,
  text: string
): Promise<TicketTimelineEntry> {
  return apiFetch<TicketTimelineEntry>(`/operator/tickets/${id}/notes/`, {
    method: "POST",
    body: JSON.stringify({ text }),
  });
}

/** Toggles the logged-in operator's own available/busy status. */
export async function updateOperatorAvailability(
  isAvailable: boolean
): Promise<OperatorAvailability> {
  return apiFetch<OperatorAvailability>("/operator/me/status/", {
    method: "PATCH",
    body: JSON.stringify({ is_available: isAvailable }),
  });
}

/**
 * Polling-based check for new OPEN tickets in the operator's department
 * since the given ISO timestamp — feeds the notification bell (Stage 2.2).
 * Real-time push replaces this in Stage 3.2.
 */
export async function getNewTicketCount(sinceIso: string): Promise<number> {
  const { count } = await apiFetch<{ count: number }>(
    `/operator/tickets/new-count/?since=${encodeURIComponent(sinceIso)}`
  );
  return count;
}

/** Count of currently-overdue tickets in the operator's department (Stage 2.9). */
export async function getOverdueTicketCount(): Promise<number> {
  const { count } = await apiFetch<{ count: number }>("/operator/tickets/overdue-count/");
  return count;
}