/**
 * The browser's side of live chat, for whichever transport the server
 * says is live.
 *
 * The page never decides this: it asks GET /chat/config/ once and gets
 * back "sse" or "websocket" (apps/chat/delivery.py). That is what makes
 * the hotel's switch to real WebSockets at deployment a server setting
 * instead of a frontend release.
 *
 *   sse        nothing to open. The live stream the panel and the guest
 *              portal already run (lib/realtime.ts) carries chat.message
 *              alongside its other events, so a message shows up within
 *              SSE_POLL_SECONDS. One stream, one server thread.
 *
 *   websocket  open a socket on the thread that is on screen, for
 *              instant delivery both ways. The stream stays running: it
 *              is what keeps the unread badge right for the threads that
 *              are *not* on screen, and it is the backstop if the socket
 *              drops.
 *
 * Either way the arrival of a message ends up as one CHAT_EVENT on the
 * window, so the thread component is written once.
 */

import { API_URL, getChatConfig, getChatSocketTicket } from "@/lib/api/client";
import type { ChatConfig, ChatMessage } from "@/lib/api/types";
import { announceChatMessage, reconnectDelay } from "@/lib/realtime";

let configPromise: Promise<ChatConfig> | null = null;

/**
 * The transport, fetched once per page load. Falls back to SSE if the
 * call fails — the transport that needs no extra infrastructure is the
 * safe thing to assume when we can't ask.
 */
export function chatConfig(): Promise<ChatConfig> {
  configPromise ??= getChatConfig().catch(
    (): ChatConfig => ({ transport: "sse", websocket_path: "", poll_seconds: 3 })
  );
  return configPromise;
}

/** Only exported so tests can start from a clean slate. */
export function resetChatConfigCache(): void {
  configPromise = null;
}

/** http://host/api/v1 → ws://host/ws/chat/<id>/ */
export function socketUrl(conversationId: number, ticket: string): string {
  const base = new URL(API_URL, window.location.origin);
  const scheme = base.protocol === "https:" ? "wss:" : "ws:";
  return `${scheme}//${base.host}/ws/chat/${conversationId}/?ticket=${encodeURIComponent(ticket)}`;
}

/**
 * Keep a socket open on one conversation until `signal` aborts.
 *
 * Every frame that arrives is announced as a CHAT_EVENT, exactly like a
 * message that came down the SSE stream, so nothing downstream knows
 * which transport delivered it. Returns a `send` the composer can use;
 * on SSE it is null and the composer posts over REST instead.
 */
export async function openChatSocket(
  conversationId: number,
  signal: AbortSignal
): Promise<{ send: (body: string) => boolean } | null> {
  const config = await chatConfig();
  if (config.transport !== "websocket") return null;

  let socket: WebSocket | null = null;
  let failures = 0;
  let closed = false;

  const connect = async () => {
    if (closed || signal.aborted) return;
    let ticket: string;
    try {
      // A fresh single-use ticket for every attempt: it is worth nothing
      // after the handshake, so a reconnect can't replay the old one.
      ({ ticket } = await getChatSocketTicket());
    } catch {
      failures += 1;
      setTimeout(connect, reconnectDelay(failures));
      return;
    }

    socket = new WebSocket(socketUrl(conversationId, ticket));

    socket.onopen = () => {
      failures = 0;
    };
    socket.onmessage = (event) => {
      try {
        announceChatMessage(JSON.parse(event.data as string) as ChatMessage);
      } catch {
        // A garbled frame isn't worth dropping the connection over.
      }
    };
    socket.onclose = () => {
      if (closed || signal.aborted) return;
      failures += 1;
      setTimeout(connect, reconnectDelay(failures));
    };
  };

  signal.addEventListener("abort", () => {
    closed = true;
    socket?.close();
  });

  await connect();

  return {
    send: (body: string) => {
      if (socket?.readyState !== WebSocket.OPEN) return false;
      socket.send(JSON.stringify({ body }));
      return true;
    },
  };
}
