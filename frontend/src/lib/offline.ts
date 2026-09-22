/**
 * Operator offline mode: read what was last loaded, queue what can safely
 * wait, and send it when the connection is back.
 *
 * Reads — readThrough() keeps the last good response of the operator GETs
 * in sessionStorage (this tab only, gone when it closes, wiped on logout)
 * and serves it when the network is down.
 *
 * Writes — only a status change (with its resolution) and an internal note
 * are queued; assignment, priority and photos need the network. The queue
 * lives in localStorage, per user, so it survives a reload. flushQueue()
 * replays it in order; before replaying a status change it re-reads the
 * ticket, and if the ticket changed in the meantime (someone else resolved
 * or reassigned it) the action is dropped and reported as a conflict
 * rather than overwriting their work.
 *
 * What it deliberately does NOT do: persist the access token. It lives in
 * memory only (see client.ts), so offline mode covers a connection that
 * drops while the panel is open, not a cold reload while offline.
 */

import type { Ticket, UpdateOperatorTicketPayload } from "@/lib/api/types";

const CACHE_PREFIX = "hcr-offline-cache:";
const QUEUE_PREFIX = "hcr-offline-queue:";
export const OFFLINE_QUEUE_EVENT = "hcr-offline-queue-changed";
export const SERVED_FROM_CACHE_EVENT = "hcr-served-from-cache";
/** A read reached the server again — whatever is on screen is live. */
export const SERVED_FRESH_EVENT = "hcr-served-fresh";
/**
 * The offline queue was replayed (sent, conflicted or refused). Pages
 * showing tickets re-read them, replacing the optimistic, queued view
 * with what the server actually holds now.
 */
export const OFFLINE_SYNCED_EVENT = "hcr-offline-synced";

/** fetch() rejects with a TypeError when the request never got an answer. */
export function isNetworkError(err: unknown): boolean {
  return err instanceof TypeError || (typeof navigator !== "undefined" && navigator.onLine === false);
}

// ---------------------------------------------------------------------------
// Read cache
// ---------------------------------------------------------------------------

interface CacheEntry<T> {
  data: T;
  savedAt: string;
}

function safeStorage(kind: "session" | "local"): Storage | null {
  try {
    return kind === "session" ? window.sessionStorage : window.localStorage;
  } catch {
    return null;
  }
}

export function cacheWrite<T>(key: string, data: T): void {
  try {
    safeStorage("session")?.setItem(
      CACHE_PREFIX + key,
      JSON.stringify({ data, savedAt: new Date().toISOString() } satisfies CacheEntry<T>)
    );
  } catch {
    // Quota or private mode: offline reads just won't have this entry.
  }
}

export function cacheRead<T>(key: string): CacheEntry<T> | null {
  try {
    const raw = safeStorage("session")?.getItem(CACHE_PREFIX + key);
    return raw ? (JSON.parse(raw) as CacheEntry<T>) : null;
  } catch {
    return null;
  }
}

/**
 * Fetch, and remember the answer; if the network is down, answer from the
 * last remembered copy instead (and announce that the page is showing
 * cached data). Any other error — 403, 404, validation — is passed through.
 */
export async function readThrough<T>(key: string, fetcher: () => Promise<T>): Promise<T> {
  try {
    const data = await fetcher();
    cacheWrite(key, data);
    window.dispatchEvent(new Event(SERVED_FRESH_EVENT));
    return data;
  } catch (err) {
    if (isNetworkError(err)) {
      const hit = cacheRead<T>(key);
      if (hit) {
        window.dispatchEvent(new CustomEvent(SERVED_FROM_CACHE_EVENT, { detail: hit.savedAt }));
        return hit.data;
      }
    }
    throw err;
  }
}

/** The last known copy of a ticket: its own detail entry, or any cached list holding it. */
export function findCachedTicket(id: number): Ticket | null {
  const detail = cacheRead<Ticket>(`operator/tickets/${id}`);
  if (detail) return detail.data;

  const storage = safeStorage("session");
  if (!storage) return null;
  for (let i = 0; i < storage.length; i++) {
    const key = storage.key(i);
    if (!key?.startsWith(`${CACHE_PREFIX}operator/tickets?`)) continue;
    const list = cacheRead<Ticket[]>(key.slice(CACHE_PREFIX.length));
    const match = list?.data.find((ticket) => ticket.id === id);
    if (match) return match;
  }
  return null;
}

// ---------------------------------------------------------------------------
// Action queue
// ---------------------------------------------------------------------------

export type QueuedAction =
  | {
      id: string;
      kind: "status";
      ticketId: number;
      ticketTitle: string;
      payload: Pick<UpdateOperatorTicketPayload, "status" | "resolution">;
      /** updated_at of the ticket the operator was looking at. */
      baseUpdatedAt: string;
      createdAt: string;
    }
  | {
      id: string;
      kind: "note";
      ticketId: number;
      ticketTitle: string;
      text: string;
      createdAt: string;
    };

type NewQueuedAction =
  | Omit<Extract<QueuedAction, { kind: "status" }>, "id" | "createdAt">
  | Omit<Extract<QueuedAction, { kind: "note" }>, "id" | "createdAt">;

function queueKey(userId: number | null): string {
  return `${QUEUE_PREFIX}${userId ?? "anonymous"}`;
}

export function getQueue(userId: number | null): QueuedAction[] {
  try {
    const raw = safeStorage("local")?.getItem(queueKey(userId));
    return raw ? (JSON.parse(raw) as QueuedAction[]) : [];
  } catch {
    return [];
  }
}

function saveQueue(userId: number | null, queue: QueuedAction[]): void {
  try {
    const storage = safeStorage("local");
    if (queue.length === 0) storage?.removeItem(queueKey(userId));
    else storage?.setItem(queueKey(userId), JSON.stringify(queue));
  } catch {
    // Nothing sensible to do; the caller already told the user it's queued.
  }
  window.dispatchEvent(new CustomEvent(OFFLINE_QUEUE_EVENT, { detail: queue.length }));
}

export function enqueue(userId: number | null, action: NewQueuedAction): QueuedAction {
  const full = {
    ...action,
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    createdAt: new Date().toISOString(),
  } as QueuedAction;
  saveQueue(userId, [...getQueue(userId), full]);
  return full;
}

export interface FlushExecutors {
  getTicket: (id: number) => Promise<Ticket>;
  updateTicket: (id: number, payload: UpdateOperatorTicketPayload) => Promise<Ticket>;
  addNote: (id: number, text: string) => Promise<unknown>;
}

export interface FlushReport {
  sent: QueuedAction[];
  /** Dropped: the ticket changed while the operator was offline. */
  conflicts: QueuedAction[];
  /** Dropped: the server refused it (e.g. no longer allowed). */
  rejected: { action: QueuedAction; message: string }[];
  /** Still offline part-way through; these stay queued. */
  remaining: number;
}

/**
 * Replay the queue in order. Stops (keeping the rest) at the first network
 * error; drops and reports conflicts and refusals, so one stale action
 * can't block everything behind it forever.
 */
export async function flushQueue(userId: number | null, exec: FlushExecutors): Promise<FlushReport> {
  const queue = getQueue(userId);
  const report: FlushReport = { sent: [], conflicts: [], rejected: [], remaining: 0 };
  // Tracks updated_at after our own replayed changes, so a second queued
  // change to the same ticket isn't mistaken for someone else's edit.
  const ourUpdatedAt = new Map<number, { base: string; now: string }>();

  let index = 0;
  for (; index < queue.length; index++) {
    const action = queue[index];
    try {
      if (action.kind === "status") {
        const current = await exec.getTicket(action.ticketId);
        const ours = ourUpdatedAt.get(action.ticketId);
        const expected = ours && ours.base === action.baseUpdatedAt ? ours.now : action.baseUpdatedAt;
        if (current.updated_at !== expected) {
          report.conflicts.push(action);
          continue;
        }
        const updated = await exec.updateTicket(action.ticketId, action.payload);
        ourUpdatedAt.set(action.ticketId, { base: action.baseUpdatedAt, now: updated.updated_at });
      } else {
        await exec.addNote(action.ticketId, action.text);
      }
      report.sent.push(action);
    } catch (err) {
      if (isNetworkError(err)) break;
      report.rejected.push({
        action,
        message: err instanceof Error ? err.message : String(err),
      });
    }
  }

  const left = queue.slice(index);
  report.remaining = left.length;
  saveQueue(userId, left);
  return report;
}

/** On logout: nothing from this operator's session may stay on the device. */
export function clearOfflineData(): void {
  for (const kind of ["session", "local"] as const) {
    const storage = safeStorage(kind);
    if (!storage) continue;
    const doomed: string[] = [];
    for (let i = 0; i < storage.length; i++) {
      const key = storage.key(i);
      if (key?.startsWith(CACHE_PREFIX) || key?.startsWith(QUEUE_PREFIX)) doomed.push(key);
    }
    doomed.forEach((key) => storage.removeItem(key));
  }
}
