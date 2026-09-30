/**
 * Stage 3.2 — the operator panel's side of the live event stream
 * (GET /operator/events/, apps/notifications/stream.py). Replaces the
 * Stage 2.2 polling bell.
 *
 * fetch() + a streaming body rather than EventSource: EventSource can't
 * send an Authorization header, and the access token must stay in memory
 * (client.ts) — no token in the URL, no cookie. The stream ends on its own
 * every few minutes (server `reconnect` event); each reconnect asks
 * getFreshAccessToken() for a valid token and passes the last cursor back,
 * so nothing that happened in between is missed.
 */

import { API_URL, getFreshAccessToken } from "@/lib/api/client";
import type { ChatMessage } from "@/lib/api/types";

export interface StreamCursor {
  ticket: number;
  history: number;
  /** Chat rides this same stream — see apps/notifications/stream.py. */
  chat: number;
}

/** The guest stream carries chat only; a guest has nothing else live. */
export interface GuestStreamCursor {
  chat: number;
}

export type OperatorEvent =
  | {
      type: "ticket.created";
      id: number;
      title: string;
      priority: string;
      category_name: string;
      room_number: string;
      assigned_to: number | null;
      cursor: StreamCursor;
    }
  | { type: "ticket.assigned"; id: number; title: string; by: string | null; cursor: StreamCursor }
  | { type: "heartbeat"; active_tickets: number; is_available: boolean; cursor: StreamCursor }
  | { type: "reconnect"; cursor: StreamCursor }
  | ({ type: "chat.message"; cursor: StreamCursor } & ChatMessage);

export type GuestEvent =
  | ({ type: "chat.message"; cursor: GuestStreamCursor } & ChatMessage)
  | { type: "heartbeat"; cursor: GuestStreamCursor }
  | { type: "reconnect"; cursor: GuestStreamCursor };

/** Page-level "something changed" signal: lists re-read when it fires. */
export const TICKET_EVENT = "hcr-ticket-event";

/**
 * A chat message arrived. Carried on a CustomEvent's `detail` so an open
 * thread can append it without another round trip, while a header that
 * only shows a count can ignore the payload.
 */
export const CHAT_EVENT = "hcr-chat-message";

export function announceChatMessage(message: ChatMessage): void {
  window.dispatchEvent(new CustomEvent<ChatMessage>(CHAT_EVENT, { detail: message }));
}

/**
 * Split an SSE text buffer into complete events. Returns the parsed events
 * and whatever incomplete tail is left for the next chunk. Unknown or
 * malformed events are skipped, never thrown on.
 */
export function parseEventStream<T = OperatorEvent>(
  buffer: string
): { events: T[]; rest: string } {
  const normalized = buffer.replace(/\r\n/g, "\n");
  const blocks = normalized.split("\n\n");
  const rest = blocks.pop() ?? "";
  const events: T[] = [];

  for (const block of blocks) {
    let name: string | null = null;
    const data: string[] = [];
    for (const line of block.split("\n")) {
      if (line.startsWith("event:")) name = line.slice(6).trim();
      else if (line.startsWith("data:")) data.push(line.slice(5).trimStart());
    }
    if (!name || data.length === 0) continue;
    try {
      events.push({ type: name, ...JSON.parse(data.join("\n")) } as T);
    } catch {
      // A garbled event isn't worth dropping the connection over.
    }
  }
  return { events, rest };
}

/** Wait before reconnecting: 2s, 4s, 8s ... capped at 30s. */
export function reconnectDelay(failures: number): number {
  return Math.min(2000 * 2 ** Math.max(0, failures - 1), 30_000);
}

const wait = (ms: number, signal: AbortSignal) =>
  new Promise<void>((resolve) => {
    const timer = setTimeout(resolve, ms);
    signal.addEventListener("abort", () => {
      clearTimeout(timer);
      resolve();
    });
  });

/**
 * Keep a live stream open until `signal` aborts, calling `onEvent` for
 * every event. Reconnects on its own after the server ends the stream, a
 * network drop, or a server error (with backoff); gives up only when the
 * session is gone (no token after a refresh).
 */
export async function runOperatorEventStream(
  onEvent: (event: OperatorEvent) => void,
  signal: AbortSignal
): Promise<void> {
  let cursor: StreamCursor | null = null;
  let failures = 0;
  let forceRefresh = false;

  while (!signal.aborted) {
    if (typeof navigator !== "undefined" && navigator.onLine === false) {
      await wait(5000, signal);
      continue;
    }

    const token = await getFreshAccessToken(forceRefresh);
    forceRefresh = false;
    if (!token) {
      failures += 1;
      if (failures > 3) return; // logged out for good
      await wait(reconnectDelay(failures), signal);
      continue;
    }

    const query = cursor
      ? `?after_ticket=${cursor.ticket}&after_history=${cursor.history}&after_chat=${cursor.chat}`
      : "";
    try {
      const response = await fetch(`${API_URL}/operator/events/${query}`, {
        headers: { Authorization: `Bearer ${token}`, Accept: "text/event-stream" },
        signal,
      });
      if (response.status === 401) {
        // Token rejected: refresh once more; if that keeps failing, the
        // session is over and the auth layer will send the user to login.
        forceRefresh = true;
        failures += 1;
        if (failures > 3) return;
        continue;
      }
      // Not an operator with a department (e.g. an admin): no stream, ever.
      if (response.status === 403) return;
      if (!response.ok || !response.body) throw new Error(`HTTP ${response.status}`);

      failures = 0;
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      for (;;) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const parsed = parseEventStream(buffer);
        buffer = parsed.rest;
        for (const event of parsed.events) {
          cursor = event.cursor;
          onEvent(event);
        }
      }
      // The server ended the stream on schedule — reconnect right away.
    } catch {
      if (signal.aborted) return;
      failures += 1;
      await wait(reconnectDelay(failures), signal);
    }
  }
}

/**
 * The guest portal's side of the same machinery (GET /guest/events/).
 *
 * A guest gets one kind of live event — a reply in their chat — so this
 * carries only that. It is deliberately the same code shape as the
 * operator stream: the token still never leaves memory, and the cursor
 * still means nothing is missed across a reconnect.
 */
export async function runGuestEventStream(
  onEvent: (event: GuestEvent) => void,
  signal: AbortSignal
): Promise<void> {
  let cursor: GuestStreamCursor | null = null;
  let failures = 0;
  let forceRefresh = false;

  while (!signal.aborted) {
    if (typeof navigator !== "undefined" && navigator.onLine === false) {
      await wait(5000, signal);
      continue;
    }

    const token = await getFreshAccessToken(forceRefresh);
    forceRefresh = false;
    if (!token) {
      failures += 1;
      if (failures > 3) return; // logged out for good
      await wait(reconnectDelay(failures), signal);
      continue;
    }

    const query = cursor ? `?after_chat=${cursor.chat}` : "";
    try {
      const response = await fetch(`${API_URL}/guest/events/${query}`, {
        headers: { Authorization: `Bearer ${token}`, Accept: "text/event-stream" },
        signal,
      });
      if (response.status === 401) {
        forceRefresh = true;
        failures += 1;
        if (failures > 3) return;
        continue;
      }
      // Not a guest (an operator opening a guest URL): no stream, ever.
      if (response.status === 403) return;
      if (!response.ok || !response.body) throw new Error(`HTTP ${response.status}`);

      failures = 0;
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      for (;;) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const parsed = parseEventStream<GuestEvent>(buffer);
        buffer = parsed.rest;
        for (const event of parsed.events) {
          cursor = event.cursor;
          onEvent(event);
        }
      }
    } catch {
      if (signal.aborted) return;
      failures += 1;
      await wait(reconnectDelay(failures), signal);
    }
  }
}
