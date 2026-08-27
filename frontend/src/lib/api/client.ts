import { clearTokens, getStoredTokens, isTokenExpired, saveTokens } from "./tokens";
import type {
  ApiErrorBody,
  AuthTokens,
  Category,
  CreateTicketPayload,
  Department,
  GuestProfile,
  OperatorColleague,
  RefreshResponse,
  Ticket,
  TicketPriority,
  TicketStatus,
  UpdateOperatorTicketPayload,
  UserRole,
} from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000/api/v1";

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
 * Fired whenever the client refreshes tokens on its own (a 401 mid-request
 * triggered a silent refresh), so AuthContext can sync its in-memory state
 * with what just got written to storage.
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

/** Raw refresh call — deliberately does not go through apiFetch (no auth header, no retry loop). */
async function refreshAccessToken(refreshToken: string): Promise<AuthTokens> {
  const response = await fetch(`${API_URL}/auth/token/refresh/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh: refreshToken }),
  });

  if (!response.ok) {
    const body = await parseErrorBody(response);
    throw new ApiError(response.status, body.message, body.errors);
  }

  const data = (await response.json()) as RefreshResponse;
  const stored = getStoredTokens();

  const newTokens: AuthTokens = {
    access: data.access,
    // simplejwt ROTATE_REFRESH_TOKENS means a new refresh token usually
    // comes back too; fall back to the old one just in case it doesn't.
    refresh: data.refresh ?? refreshToken,
    role: stored?.role ?? "GUEST",
  };

  saveTokens(newTokens);
  notifyTokensChanged(newTokens);

  return newTokens;
}

interface ApiFetchOptions extends RequestInit {
  /** Skip attaching an Authorization header (for login endpoints, etc). */
  skipAuth?: boolean;
}

export async function apiFetch<T>(path: string, options: ApiFetchOptions = {}): Promise<T> {
  const { skipAuth = false, headers, ...rest } = options;

  let tokens = getStoredTokens();

  if (!skipAuth && tokens && isTokenExpired(tokens.access)) {
    try {
      tokens = await refreshAccessToken(tokens.refresh);
    } catch {
      clearTokens();
      notifyTokensChanged(null);
      tokens = null;
    }
  }

  const requestHeaders = new Headers(headers);
  requestHeaders.set("Content-Type", "application/json");
  if (!skipAuth && tokens) {
    requestHeaders.set("Authorization", `Bearer ${tokens.access}`);
  }

  let response = await fetch(`${API_URL}${path}`, { ...rest, headers: requestHeaders });

  // One retry after a silent refresh, in case the token expired mid-flight
  // (clock skew, a long-running request, etc).
  if (response.status === 401 && !skipAuth && tokens) {
    try {
      const refreshed = await refreshAccessToken(tokens.refresh);
      requestHeaders.set("Authorization", `Bearer ${refreshed.access}`);
      response = await fetch(`${API_URL}${path}`, { ...rest, headers: requestHeaders });
    } catch {
      clearTokens();
      notifyTokensChanged(null);
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
  return apiFetch<AuthTokens>("/auth/guest/login/", {
    method: "POST",
    skipAuth: true,
    body: JSON.stringify({ national_id: nationalId, room_number: roomNumber }),
  });
}

export async function loginOperator(username: string, password: string): Promise<AuthTokens> {
  return apiFetch<AuthTokens>("/auth/operator/login/", {
    method: "POST",
    skipAuth: true,
    body: JSON.stringify({ username, password }),
  });
}

export function getCurrentRole(): UserRole | null {
  return getStoredTokens()?.role ?? null;
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