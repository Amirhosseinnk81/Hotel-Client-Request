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
  refresh: string;
  role: UserRole;
}

export interface RefreshResponse {
  access: string;
  refresh?: string;
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
}

export type TicketStatus = "OPEN" | "IN_PROGRESS" | "RESOLVED" | "CANCELLED";
export type TicketPriority = "LOW" | "NORMAL" | "HIGH" | "URGENT";

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
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
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
}