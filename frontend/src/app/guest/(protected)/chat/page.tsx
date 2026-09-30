"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight, MessagesSquare } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ChatThread } from "@/components/chat/chat-thread";
import { FormError } from "@/components/form-error";
import { useLocale } from "@/contexts/locale-context";
import {
  ApiError,
  getAccessToken,
  getConversations,
  getDepartments,
  startGuestConversation,
} from "@/lib/api/client";
import { decodeAccessToken } from "@/lib/api/tokens";
import type { Conversation, Department } from "@/lib/api/types";

/**
 * The guest's side of live chat: pick a team, then talk.
 *
 * A thread per department, reused across the stay — a guest who asked
 * housekeeping two things is in one conversation, not two, so the
 * operator answers in a window the guest still has open.
 *
 * Department names are hotel-entered data and stay untranslated, the same
 * rule as the request form.
 */
export default function GuestChatPage() {
  const { t } = useLocale();

  const [departments, setDepartments] = useState<Department[] | null>(null);
  const [conversations, setConversations] = useState<Conversation[] | null>(null);
  const [open, setOpen] = useState<Conversation | null>(null);
  const [starting, setStarting] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const myUserId = decodeAccessToken(getAccessToken() ?? "")?.user_id ?? null;

  useEffect(() => {
    let cancelled = false;
    Promise.all([getDepartments(), getConversations()])
      .then(([rows, threads]) => {
        if (cancelled) return;
        setDepartments(rows.filter((row) => row.is_active));
        setConversations(threads);
        // Straight into the conversation that has been talked in most
        // recently — a guest coming back to read a reply shouldn't have
        // to pick the department again.
        const latest = threads.find((thread) => !thread.is_closed);
        if (latest) setOpen(latest);
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
  }, []);

  const start = async (department: Department) => {
    setStarting(department.id);
    setError(null);
    try {
      const conversation = await startGuestConversation(department.id);
      setOpen(conversation);
      setConversations((current) => {
        const rest = (current ?? []).filter((row) => row.id !== conversation.id);
        return [conversation, ...rest];
      });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("chat.startError"));
    } finally {
      setStarting(null);
    }
  };

  return (
    <main className="mx-auto flex w-full max-w-lg flex-1 flex-col gap-4">
      <Button asChild variant="ghost" size="sm" className="w-fit gap-1.5">
        <Link href="/guest">
          <ArrowRight className="size-3.5 ltr:rotate-180" />
          {t("common.back")}
        </Link>
      </Button>

      <div>
        <h1 className="display-2 rule-accent">{t("chat.title")}</h1>
        <p className="pt-2 text-sm text-muted-foreground">{t("chat.subtitle")}</p>
      </div>

      {error && <FormError message={error} />}

      {!departments && !error && (
        <div className="flex flex-col gap-2">
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
        </div>
      )}

      {open ? (
        <Card className="flex min-h-96 flex-1 flex-col">
          <CardHeader className="flex-row items-center justify-between gap-3 space-y-0">
            <CardTitle className="flex items-center gap-2 text-base font-medium">
              <MessagesSquare className="size-4 text-primary" />
              {open.department_name || t("chat.title")}
            </CardTitle>
            <Button variant="ghost" size="sm" onClick={() => setOpen(null)}>
              {t("chat.changeDepartment")}
            </Button>
          </CardHeader>
          <CardContent className="flex min-h-0 flex-1 flex-col">
            <ChatThread
              key={open.id}
              conversationId={open.id}
              isClosed={open.is_closed}
              myUserId={myUserId}
            />
          </CardContent>
        </Card>
      ) : (
        departments && (
          <Card>
            <CardHeader>
              <CardTitle className="text-base font-medium">{t("chat.pickDepartment")}</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-2">
              {departments.map((department) => {
                const existing = conversations?.find(
                  (row) => row.department === department.id && !row.is_closed
                );
                return (
                  <Button
                    key={department.id}
                    variant="outline"
                    className="justify-between gap-2"
                    disabled={starting !== null}
                    onClick={() => void start(department)}
                  >
                    <span>{department.name}</span>
                    <span className="text-xs text-muted-foreground">
                      {starting === department.id
                        ? t("chat.starting")
                        : existing && existing.unread > 0
                          ? existing.unread === 1
                            ? t("chat.unreadOne")
                            : t("chat.unreadMany", { count: String(existing.unread) })
                          : t("chat.start")}
                    </span>
                  </Button>
                );
              })}
            </CardContent>
          </Card>
        )
      )}
    </main>
  );
}
