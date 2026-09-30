"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Send } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { FormError } from "@/components/form-error";
import { useOptionalLocale } from "@/contexts/locale-context";
import { ApiError, getChatMessages, markConversationRead, sendChatMessage } from "@/lib/api/client";
import type { ChatMessage } from "@/lib/api/types";
import { openChatSocket } from "@/lib/chat";
import { formatDateTime } from "@/lib/format";
import { CHAT_EVENT } from "@/lib/realtime";

/**
 * One open conversation: the messages, and the box to add to them.
 *
 * Shared between the guest portal and the operator panel on purpose —
 * it is the same thread from two ends, and a second copy would be where
 * the two drift apart on who wrote what. `useOptionalLocale` gives it
 * the guest's language inside the portal and Persian outside it, the
 * same trick RelativeTime and the PDF button use.
 *
 * Live arrival comes from one window event (CHAT_EVENT), whichever
 * transport delivered it — see lib/chat.ts.
 */
export function ChatThread({
  conversationId,
  isClosed = false,
  myUserId,
}: {
  conversationId: number;
  isClosed?: boolean;
  /** Only used to put my own messages on the other side of the thread. */
  myUserId: number | null;
}) {
  const { t, locale } = useOptionalLocale();

  const [messages, setMessages] = useState<ChatMessage[] | null>(null);
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottom = useRef<HTMLDivElement | null>(null);
  const socket = useRef<{ send: (body: string) => boolean } | null>(null);

  const add = useCallback((message: ChatMessage) => {
    setMessages((current) => {
      if (!current) return current;
      // The same message can arrive twice — once as the POST's response
      // and once off the stream or the socket. Keyed by id, so it can't
      // show up as two bubbles.
      if (current.some((existing) => existing.id === message.id)) return current;
      return [...current, message];
    });
  }, []);

  // No reset of `messages` here: both callers give this component a
  // `key={conversationId}`, so switching threads remounts it rather than
  // showing the previous thread's bubbles while the new one loads.
  useEffect(() => {
    let cancelled = false;
    getChatMessages(conversationId)
      .then((rows) => {
        if (!cancelled) setMessages(rows);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : t("chat.loadError"));
        }
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- t only changes the fallback text
  }, [conversationId]);

  // Live arrival. One listener whatever the transport: on SSE the panel's
  // or the portal's stream announces it; on WebSockets the socket below
  // announces the very same event.
  useEffect(() => {
    const onChat = (event: Event) => {
      const message = (event as CustomEvent<ChatMessage>).detail;
      if (message?.conversation !== conversationId) return;
      add(message);
      // Reading it as it arrives — otherwise the badge counts a message
      // the operator is looking at.
      void markConversationRead(conversationId).catch(() => {});
    };
    window.addEventListener(CHAT_EVENT, onChat);
    return () => window.removeEventListener(CHAT_EVENT, onChat);
  }, [conversationId, add]);

  // The WebSocket transport, when the server says it is live. On SSE this
  // resolves to null and everything still works over REST + the stream.
  useEffect(() => {
    const controller = new AbortController();
    void openChatSocket(conversationId, controller.signal)
      .then((connection) => {
        socket.current = connection;
      })
      .catch(() => {
        socket.current = null;
      });
    return () => {
      controller.abort();
      socket.current = null;
    };
  }, [conversationId]);

  useEffect(() => {
    bottom.current?.scrollIntoView({ block: "end" });
  }, [messages]);

  const send = async () => {
    const body = draft.trim();
    if (!body || sending) return;

    setSending(true);
    setError(null);
    try {
      // Always over REST, even on the WebSocket transport: the write has
      // to be confirmed, and a socket send is fire-and-forget. The socket
      // is how the *other* side hears about it, not how it gets stored.
      const message = await sendChatMessage(conversationId, body);
      add(message);
      setDraft("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("chat.sendError"));
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-3">
      <div className="flex min-h-64 flex-1 flex-col gap-3 overflow-y-auto border p-4">
        {!messages && !error && (
          <>
            <Skeleton className="h-12 w-2/3" />
            <Skeleton className="h-12 w-1/2 self-end" />
            <Skeleton className="h-12 w-3/5" />
          </>
        )}

        {messages?.length === 0 && (
          <p className="m-auto text-sm text-muted-foreground">{t("chat.empty")}</p>
        )}

        {messages?.map((message) => {
          const mine = myUserId !== null && message.sender === myUserId;
          return (
            <div
              key={message.id}
              className={`flex max-w-[85%] flex-col gap-1 ${mine ? "self-end" : "self-start"}`}
            >
              {/*
                Always named, never an anonymous bubble: in five-star
                usability testing guests could not tell whether there was
                a person on the other end (CLAUDE.md backlog).
              */}
              <span className="text-xs text-muted-foreground">
                {mine ? t("chat.you") : message.sender_label}
              </span>
              <div
                className={`whitespace-pre-wrap border px-3 py-2 text-sm ${
                  mine ? "bg-muted" : "bg-card"
                }`}
              >
                {message.body}
              </div>
              <span className="text-[11px] text-muted-foreground">
                {formatDateTime(message.created_at, locale)}
              </span>
            </div>
          );
        })}
        <div ref={bottom} />
      </div>

      {error && <FormError message={error} />}

      {isClosed ? (
        <p className="text-sm text-muted-foreground">{t("chat.closed")}</p>
      ) : (
        <div className="flex items-end gap-2">
          <Textarea
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={(event) => {
              // Enter sends, Shift+Enter starts a new line — what people
              // expect of a chat box rather than a form field.
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                void send();
              }
            }}
            rows={2}
            maxLength={4000}
            placeholder={t("chat.placeholder")}
            className="flex-1 resize-none"
          />
          <Button
            onClick={() => void send()}
            disabled={sending || !draft.trim()}
            className="gap-1.5"
          >
            <Send className="size-3.5 ltr:rotate-180" />
            {sending ? t("chat.sending") : t("chat.send")}
          </Button>
        </div>
      )}
    </div>
  );
}
