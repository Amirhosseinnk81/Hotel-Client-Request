"use client";

import { useCallback, useEffect, useState } from "react";
import { MessageSquarePlus, MessagesSquare, RefreshCw } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { ChatThread } from "@/components/chat/chat-thread";
import { FormError } from "@/components/form-error";
import { RelativeTime } from "@/components/relative-time";
import { toast } from "@/hooks/use-toast";
import {
  ApiError,
  getAccessToken,
  getConversations,
  getOperatorColleagues,
  startStaffConversation,
} from "@/lib/api/client";
import { decodeAccessToken } from "@/lib/api/tokens";
import type { Conversation, OperatorColleague } from "@/lib/api/types";
import { formatNumber } from "@/lib/format";
import { CHAT_EVENT } from "@/lib/realtime";

/**
 * The panel's chat inbox: guests of this department asking for something,
 * and colleagues talking to each other.
 *
 * One list for both, because the backend keeps them in one table for the
 * same reason — the messages, the unread counting and the live delivery
 * are identical, and the only difference is who is in the thread.
 */
export default function OperatorChatPage() {
  const [conversations, setConversations] = useState<Conversation[] | null>(null);
  const [openId, setOpenId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [newOpen, setNewOpen] = useState(false);
  const [colleagues, setColleagues] = useState<OperatorColleague[] | null>(null);
  const [picked, setPicked] = useState<number[]>([]);
  const [subject, setSubject] = useState("");
  const [starting, setStarting] = useState(false);

  const payload = decodeAccessToken(getAccessToken() ?? "");
  const myUserId = payload?.user_id ?? null;
  // The colleagues list is department-scoped, and an admin has no
  // department — so they read and answer threads they are in, but don't
  // get the "start one with a colleague" button.
  const role = payload?.role ?? null;

  const load = useCallback(() => {
    return getConversations()
      .then((rows) => {
        setConversations(rows);
        setError(null);
      })
      .catch((err) => {
        setError(err instanceof ApiError ? err.message : "خطا در دریافت گفت‌وگوها.");
      });
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  // Re-read the inbox when a message arrives anywhere: the open thread
  // appends it itself, but the list's ordering and unread counts are
  // server-side numbers.
  useEffect(() => {
    const onChat = () => void load();
    window.addEventListener(CHAT_EVENT, onChat);
    return () => window.removeEventListener(CHAT_EVENT, onChat);
  }, [load]);

  const openNewDialog = () => {
    setNewOpen(true);
    if (colleagues === null) {
      getOperatorColleagues()
        .then(setColleagues)
        .catch(() => setColleagues([]));
    }
  };

  const startStaffThread = async () => {
    if (picked.length === 0) return;
    setStarting(true);
    try {
      const conversation = await startStaffConversation(picked, subject.trim());
      await load();
      setOpenId(conversation.id);
      setNewOpen(false);
      setPicked([]);
      setSubject("");
    } catch (err) {
      toast({
        title: "گفت‌وگو باز نشد",
        description: err instanceof ApiError ? err.message : "لطفاً دوباره تلاش کنید.",
        variant: "destructive",
      });
    } finally {
      setStarting(false);
    }
  };

  const open = conversations?.find((row) => row.id === openId) ?? null;

  return (
    <main className="flex flex-1 flex-col gap-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h1 className="display-2 rule-accent">گفت‌وگو</h1>
          <p className="pt-2 text-sm text-muted-foreground">
            پشتیبانی لحظه‌ای مهمانان واحد شما، و گفت‌وگو با همکاران.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="ghost" size="sm" className="gap-1.5" onClick={() => void load()}>
            <RefreshCw className="size-3.5" />
            به‌روزرسانی
          </Button>
          {role === "OPERATOR" && (
            <Button size="sm" className="gap-1.5" onClick={openNewDialog}>
              <MessageSquarePlus className="size-3.5" />
              گفت‌وگوی تازه با همکار
            </Button>
          )}
        </div>
      </div>

      {error && <FormError message={error} />}

      <div className="grid flex-1 grid-cols-1 gap-4 lg:grid-cols-[22rem_1fr]">
        <Card className="flex max-h-[32rem] flex-col overflow-hidden lg:max-h-none">
          <CardHeader>
            <CardTitle className="text-base font-medium">گفت‌وگوها</CardTitle>
          </CardHeader>
          <CardContent className="flex min-h-0 flex-1 flex-col gap-1 overflow-y-auto">
            {!conversations &&
              !error &&
              [0, 1, 2].map((i) => <Skeleton key={i} className="h-14 w-full" />)}

            {conversations?.length === 0 && (
              <p className="text-sm text-muted-foreground">هنوز گفت‌وگویی نیست.</p>
            )}

            {conversations?.map((conversation) => (
              <button
                key={conversation.id}
                type="button"
                onClick={() => setOpenId(conversation.id)}
                className={`flex flex-col gap-1 border p-3 text-start transition-colors ${
                  conversation.id === openId
                    ? "border-accent bg-muted"
                    : "border-transparent hover:bg-muted/60"
                }`}
              >
                <span className="flex items-center justify-between gap-2 text-sm">
                  <span className="truncate">
                    {conversation.kind === "GUEST"
                      ? `${conversation.guest_name || "مهمان"}${
                          conversation.room_number ? ` — اتاق ${conversation.room_number}` : ""
                        }`
                      : conversation.title}
                  </span>
                  {conversation.unread > 0 && (
                    <Badge
                      variant="destructive"
                      className="h-4 min-w-4 justify-center rounded-full p-0 text-[10px]"
                    >
                      {formatNumber(conversation.unread)}
                    </Badge>
                  )}
                </span>
                <span className="truncate text-xs text-muted-foreground">
                  {conversation.last_message || "—"}
                </span>
                <span className="text-[11px] text-muted-foreground">
                  {conversation.kind === "GUEST" ? conversation.department_name : "همکاران"}
                  {conversation.last_message_at && (
                    <>
                      {" · "}
                      <RelativeTime iso={conversation.last_message_at} />
                    </>
                  )}
                </span>
              </button>
            ))}
          </CardContent>
        </Card>

        <Card className="flex min-h-96 flex-col">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base font-medium">
              <MessagesSquare className="size-4 text-primary" />
              {open
                ? open.kind === "GUEST"
                  ? `${open.guest_name || "مهمان"}${
                      open.room_number ? ` — اتاق ${open.room_number}` : ""
                    }`
                  : open.title
                : "یک گفت‌وگو را انتخاب کنید"}
            </CardTitle>
          </CardHeader>
          <CardContent className="flex min-h-0 flex-1 flex-col">
            {open ? (
              <ChatThread
                key={open.id}
                conversationId={open.id}
                isClosed={open.is_closed}
                myUserId={myUserId}
              />
            ) : (
              <p className="m-auto text-sm text-muted-foreground">
                از فهرست سمت راست یک گفت‌وگو را باز کنید.
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      <Dialog open={newOpen} onOpenChange={setNewOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>گفت‌وگوی تازه با همکار</DialogTitle>
            <DialogDescription>
              یک یا چند همکار را انتخاب کنید. موضوع اختیاری است؛ بدون موضوع، گفت‌وگوی قبلی با
              همان افراد دوباره باز می‌شود تا فهرست پر از گفت‌وگوی خالی نشود.
            </DialogDescription>
          </DialogHeader>

          <div className="flex flex-col gap-3">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="chat-subject">موضوع (اختیاری)</Label>
              <Input
                id="chat-subject"
                value={subject}
                onChange={(event) => setSubject(event.target.value)}
                maxLength={150}
                placeholder="مثلاً: هماهنگی شیفت شب"
              />
            </div>

            <div className="flex max-h-56 flex-col gap-1 overflow-y-auto border p-2">
              {!colleagues && <Skeleton className="h-8 w-full" />}
              {colleagues?.length === 0 && (
                <p className="p-1 text-sm text-muted-foreground">همکاری برای نمایش نیست.</p>
              )}
              {colleagues?.map((colleague) => {
                const checked = picked.includes(colleague.id);
                return (
                  <label
                    key={colleague.id}
                    className="flex cursor-pointer items-center gap-2 p-1.5 text-sm hover:bg-muted"
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() =>
                        setPicked((current) =>
                          checked
                            ? current.filter((id) => id !== colleague.id)
                            : [...current, colleague.id]
                        )
                      }
                    />
                    <span>{colleague.username}</span>
                    {/* The same busy/available wording as everywhere else. */}
                    <span className="ms-auto text-xs text-muted-foreground">
                      {colleague.is_available
                        ? "در دسترس"
                        : `مشغول — ${formatNumber(colleague.active_tickets)}`}
                    </span>
                  </label>
                );
              })}
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setNewOpen(false)}>
              انصراف
            </Button>
            <Button
              onClick={() => void startStaffThread()}
              disabled={starting || picked.length === 0}
            >
              {starting ? "در حال باز کردن…" : "شروع گفت‌وگو"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </main>
  );
}
