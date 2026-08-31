"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import {
  ArrowRight,
  CheckCircle2,
  Clock,
  Loader2,
  MessageSquarePlus,
  UserPlus,
} from "lucide-react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { FormError } from "@/components/form-error";
import { toast } from "@/hooks/use-toast";
import {
  addOperatorTicketNote,
  assignTicketToSelf,
  getAccessToken,
  getOperatorColleagues,
  getOperatorTicketDetail,
  getOperatorTicketHistory,
  updateOperatorTicket,
  ApiError,
} from "@/lib/api/client";
import { decodeAccessToken } from "@/lib/api/tokens";
import type {
  OperatorColleague,
  Ticket,
  TicketHistoryEntry,
  TicketStatus,
  TicketTimelineEntry,
} from "@/lib/api/types";
import {
  statusLabels,
  statusBadgeVariant,
  priorityLabels,
  priorityBadgeVariant,
} from "@/lib/ticket-labels";

function formatDate(iso: string) {
  return new Intl.DateTimeFormat("fa-IR", {
    year: "numeric",
    month: "long",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(iso));
}

/** Turns one TicketHistory entry into a single human-readable Persian line. */
function describeHistoryEntry(entry: TicketHistoryEntry): string {
  const statusLabel = (value: string | null) =>
    value && value in statusLabels ? statusLabels[value as TicketStatus] : value;
  const priorityLabel = (value: string | null) =>
    value && value in priorityLabels ? priorityLabels[value as keyof typeof priorityLabels] : value;

  switch (entry.action) {
    case "CREATED":
      return "درخواست ثبت شد.";
    case "ASSIGNED":
      return entry.old_value
        ? `اختصاص از ${entry.old_value} به ${entry.new_value ?? "—"} تغییر کرد.`
        : `به ${entry.new_value ?? "—"} اختصاص یافت.`;
    case "STATUS_CHANGED":
      return `وضعیت از «${statusLabel(entry.old_value)}» به «${statusLabel(entry.new_value)}» تغییر کرد.`;
    case "PRIORITY_CHANGED":
      return `اولویت از «${priorityLabel(entry.old_value)}» به «${priorityLabel(entry.new_value)}» تغییر کرد.`;
    default:
      return entry.action_display;
  }
}

/** Business rule: OPEN → IN_PROGRESS → RESOLVED, or OPEN/IN_PROGRESS → CANCELLED. */
const allowedNextStatuses: Record<TicketStatus, TicketStatus[]> = {
  OPEN: ["IN_PROGRESS", "CANCELLED"],
  IN_PROGRESS: ["RESOLVED", "CANCELLED"],
  RESOLVED: [],
  CANCELLED: [],
};

/** Sentinel value for the "no one" option — Radix Select rejects an empty string value. */
const UNASSIGNED_VALUE = "UNASSIGNED";

export default function OperatorTicketDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);

  const [ticket, setTicket] = useState<Ticket | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [isAssigning, setIsAssigning] = useState(false);

  const [colleagues, setColleagues] = useState<OperatorColleague[] | null>(null);
  const [selectedAssignee, setSelectedAssignee] = useState<string>(UNASSIGNED_VALUE);
  const [isReassigning, setIsReassigning] = useState(false);

  const [targetStatus, setTargetStatus] = useState<TicketStatus | "">("");
  const [resolution, setResolution] = useState("");
  const [isUpdating, setIsUpdating] = useState(false);

  const [timeline, setTimeline] = useState<TicketTimelineEntry[] | null>(null);
  const [timelineError, setTimelineError] = useState<string | null>(null);
  const [noteText, setNoteText] = useState("");
  const [isAddingNote, setIsAddingNote] = useState(false);

  const currentUserId = decodeAccessToken(getAccessToken() ?? "")?.user_id ?? null;

  const loadTimeline = () => {
    queueMicrotask(() => setTimelineError(null));
    getOperatorTicketHistory(id)
      .then(setTimeline)
      .catch((err) => {
        setTimelineError(
          err instanceof ApiError ? err.message : "خطا در دریافت تاریخچهٔ درخواست."
        );
      });
  };

  const load = () => {
    // Deferred (not synchronous) so calling load() directly from a
    // useEffect body doesn't trip react-hooks/set-state-in-effect — this
    // function is also called from an effect on mount/id-change.
    queueMicrotask(() => setError(null));
    getOperatorTicketDetail(id)
      .then((data) => {
        setTicket(data);
        setTargetStatus("");
        setResolution("");
        setSelectedAssignee(
          data.assigned_to != null ? String(data.assigned_to) : UNASSIGNED_VALUE
        );
      })
      .catch((err) => {
        setError(
          err instanceof ApiError && err.status === 404
            ? "چنین درخواستی یافت نشد."
            : err instanceof ApiError
              ? err.message
              : "خطا در دریافت جزئیات درخواست."
        );
      });
  };

  useEffect(() => {
    load();
    loadTimeline();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  useEffect(() => {
    getOperatorColleagues()
      .then(setColleagues)
      .catch(() => {
        toast({
          title: "خطا در دریافت لیست اپراتورها",
          description: "فهرست همکاران واحد بارگذاری نشد؛ اختصاص به شخص دیگر موقتاً در دسترس نیست.",
          variant: "destructive",
        });
        setColleagues([]);
      });
  }, []);

  const handleAssign = async () => {
    setIsAssigning(true);
    try {
      const updated = await assignTicketToSelf(id);
      setTicket(updated);
      setSelectedAssignee(
        updated.assigned_to != null ? String(updated.assigned_to) : UNASSIGNED_VALUE
      );
      loadTimeline();
      toast({
        title: "اختصاص انجام شد",
        description: "این درخواست به شما اختصاص داده شد.",
        variant: "success",
      });
    } catch (err) {
      toast({
        title: "خطا در اختصاص",
        description: err instanceof ApiError ? err.message : "خطا در اختصاص درخواست.",
        variant: "destructive",
      });
    } finally {
      setIsAssigning(false);
    }
  };

  const handleReassign = async () => {
    setIsReassigning(true);
    try {
      const updated = await updateOperatorTicket(id, {
        assigned_to: selectedAssignee === UNASSIGNED_VALUE ? null : Number(selectedAssignee),
      });
      setTicket(updated);
      loadTimeline();
      toast({
        title: "اختصاص به‌روزرسانی شد",
        description: updated.assigned_to_username
          ? `این درخواست به ${updated.assigned_to_username} اختصاص یافت.`
          : "اختصاص این درخواست برداشته شد.",
        variant: "success",
      });
    } catch (err) {
      toast({
        title: "خطا در اختصاص",
        description: err instanceof ApiError ? err.message : "خطا در به‌روزرسانی اختصاص.",
        variant: "destructive",
      });
    } finally {
      setIsReassigning(false);
    }
  };

  const handleUpdateStatus = async () => {
    if (!targetStatus) return;
    setIsUpdating(true);
    try {
      const updated = await updateOperatorTicket(id, {
        status: targetStatus,
        ...(targetStatus === "RESOLVED" ? { resolution } : {}),
      });
      setTicket(updated);
      setTargetStatus("");
      setResolution("");
      loadTimeline();
      toast({
        title: "وضعیت به‌روزرسانی شد",
        description: `وضعیت درخواست به «${statusLabels[updated.status]}» تغییر کرد.`,
        variant: "success",
      });
    } catch (err) {
      toast({
        title: "خطا در تغییر وضعیت",
        description: err instanceof ApiError ? err.message : "خطا در تغییر وضعیت.",
        variant: "destructive",
      });
    } finally {
      setIsUpdating(false);
    }
  };

  const handleAddNote = async () => {
    if (!noteText.trim()) return;
    setIsAddingNote(true);
    try {
      await addOperatorTicketNote(id, noteText.trim());
      setNoteText("");
      loadTimeline();
      toast({
        title: "یادداشت ثبت شد",
        variant: "success",
      });
    } catch (err) {
      toast({
        title: "خطا در ثبت یادداشت",
        description: err instanceof ApiError ? err.message : "خطا در ثبت یادداشت.",
        variant: "destructive",
      });
    } finally {
      setIsAddingNote(false);
    }
  };

  const options = ticket ? allowedNextStatuses[ticket.status] : [];
  const isClosed = ticket?.status === "RESOLVED" || ticket?.status === "CANCELLED";
  const isAssignedToMe = ticket?.assigned_to !== null && ticket?.assigned_to === currentUserId;
  const needsResolution = targetStatus === "RESOLVED";
  const canSubmitStatus =
    !!targetStatus && (!needsResolution || resolution.trim().length > 0);
  const currentAssigneeValue = ticket?.assigned_to != null ? String(ticket.assigned_to) : UNASSIGNED_VALUE;
  const canSubmitReassign = selectedAssignee !== currentAssigneeValue;

  return (
    <main className="mx-auto flex w-full max-w-lg flex-1 flex-col gap-4">
      <Button asChild variant="ghost" size="sm" className="w-fit gap-1.5">
        <Link href="/operator">
          <ArrowRight className="size-3.5" />
          بازگشت به لیست درخواست‌ها
        </Link>
      </Button>

      {!ticket && !error && (
        <Card>
          <CardHeader>
            <div className="flex items-start justify-between gap-2">
              <Skeleton className="h-5 w-40" />
              <Skeleton className="h-5 w-16 rounded-full" />
            </div>
            <Skeleton className="h-3.5 w-32" />
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <div className="flex gap-2">
              <Skeleton className="h-5 w-20 rounded-full" />
              <Skeleton className="h-5 w-24 rounded-full" />
            </div>
            <div className="flex flex-col gap-2">
              <Skeleton className="h-3 w-16" />
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-3/4" />
            </div>
          </CardContent>
        </Card>
      )}

      {error && (
        <Card>
          <CardContent className="pt-6">
            <FormError message={error} />
          </CardContent>
        </Card>
      )}

      {ticket && (
        <>
          <Card>
            <CardHeader>
              <div className="flex items-start justify-between gap-2">
                <CardTitle className="text-lg">{ticket.title}</CardTitle>
                <Badge variant={statusBadgeVariant[ticket.status]}>
                  {statusLabels[ticket.status]}
                </Badge>
              </div>
              <CardDescription>
                اتاق {ticket.room_number} · {ticket.category_name}
              </CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-4">
              <div className="flex flex-wrap gap-2">
                <Badge variant={priorityBadgeVariant[ticket.priority]}>
                  اولویت: {priorityLabels[ticket.priority]}
                </Badge>
                <Badge variant="secondary">
                  {ticket.assigned_to_username
                    ? `اختصاص به: ${ticket.assigned_to_username}`
                    : "اختصاص‌نیافته"}
                </Badge>
              </div>

              <div className="flex flex-col gap-1">
                <span className="text-xs text-muted-foreground">توضیحات</span>
                <p className="text-sm">{ticket.description}</p>
              </div>

              <div className="grid grid-cols-2 gap-3 text-xs text-muted-foreground">
                <span>ثبت‌شده: {formatDate(ticket.created_at)}</span>
                <span>آخرین به‌روزرسانی: {formatDate(ticket.updated_at)}</span>
              </div>

              {ticket.status === "RESOLVED" && ticket.resolution && (
                <div className="flex flex-col gap-1 rounded-lg border border-success/30 bg-success/10 p-3">
                  <div className="flex items-center gap-1.5 text-sm font-medium text-success">
                    <CheckCircle2 className="size-4" />
                    نتیجهٔ رسیدگی
                  </div>
                  <p className="text-sm">{ticket.resolution}</p>
                  {ticket.resolved_at && (
                    <span className="text-xs text-muted-foreground">
                      زمان حل: {formatDate(ticket.resolved_at)}
                    </span>
                  )}
                </div>
              )}
            </CardContent>
          </Card>

          {!isClosed && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">اختصاص درخواست</CardTitle>
                <CardDescription>
                  این درخواست را به خودتان یا یکی دیگر از اپراتورهای واحد اختصاص دهید.
                </CardDescription>
              </CardHeader>
              <CardContent className="flex flex-col gap-3">
                <div className="flex flex-col gap-1.5">
                  <Label>اپراتور</Label>
                  <Select
                    value={selectedAssignee}
                    onValueChange={setSelectedAssignee}
                    disabled={colleagues === null}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="در حال بارگذاری…" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value={UNASSIGNED_VALUE}>بدون اختصاص</SelectItem>
                      {colleagues?.map((colleague) => (
                        <SelectItem key={colleague.id} value={String(colleague.id)}>
                          <span className="flex items-center gap-1.5">
                            <span
                              aria-hidden
                              className={`size-2 rounded-full ${
                                colleague.is_available ? "bg-emerald-500" : "bg-muted-foreground/40"
                              }`}
                              title={colleague.is_available ? "در دسترس" : "مشغول"}
                            />
                            {colleague.username}
                            {colleague.id === currentUserId ? " (خودم)" : ""}
                          </span>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="flex flex-wrap gap-2">
                  <Button
                    size="sm"
                    className="w-fit gap-1.5"
                    disabled={!canSubmitReassign || isReassigning}
                    onClick={handleReassign}
                  >
                    {isReassigning && <Loader2 className="size-3.5 animate-spin" />}
                    {isReassigning ? "در حال ثبت…" : "ثبت اختصاص"}
                  </Button>

                  {!isAssignedToMe && (
                    <Button
                      size="sm"
                      variant="secondary"
                      className="w-fit gap-1.5"
                      disabled={isAssigning}
                      onClick={handleAssign}
                    >
                      {isAssigning ? (
                        <Loader2 className="size-3.5 animate-spin" />
                      ) : (
                        <UserPlus className="size-3.5" />
                      )}
                      {isAssigning ? "در حال اختصاص…" : "اختصاص به خودم"}
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          )}

          {options.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">تغییر وضعیت</CardTitle>
                {!isAssignedToMe && ticket.assigned_to && (
                  <CardDescription>
                    این درخواست به اپراتور دیگری اختصاص داده شده.
                  </CardDescription>
                )}
              </CardHeader>
              <CardContent className="flex flex-col gap-3">
                <div className="flex flex-col gap-1.5">
                  <Label>وضعیت جدید</Label>
                  <Select
                    value={targetStatus}
                    onValueChange={(v) => setTargetStatus(v as TicketStatus)}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="انتخاب کنید…" />
                    </SelectTrigger>
                    <SelectContent>
                      {options.map((status) => (
                        <SelectItem key={status} value={status}>
                          {statusLabels[status]}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {needsResolution && (
                  <div className="flex flex-col gap-1.5">
                    <Label htmlFor="resolution">نتیجهٔ رسیدگی</Label>
                    <Textarea
                      id="resolution"
                      placeholder="توضیح دهید که چه اقدامی انجام شد…"
                      value={resolution}
                      onChange={(e) => setResolution(e.target.value)}
                    />
                  </div>
                )}

                <Button
                  className="w-fit gap-1.5"
                  disabled={!canSubmitStatus || isUpdating}
                  onClick={handleUpdateStatus}
                >
                  {isUpdating && <Loader2 className="size-3.5 animate-spin" />}
                  {isUpdating ? "در حال ثبت…" : "ثبت تغییر وضعیت"}
                </Button>
              </CardContent>
            </Card>
          )}

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-1.5 text-base">
                <Clock className="size-4" />
                تایم‌لاین
              </CardTitle>
              <CardDescription>
                تاریخچهٔ رویدادها و یادداشت‌های داخلی این درخواست، به‌ترتیب زمانی.
              </CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-4">
              {timelineError && <FormError message={timelineError} />}

              {!timeline && !timelineError && (
                <div className="flex flex-col gap-3">
                  <Skeleton className="h-10 w-full" />
                  <Skeleton className="h-10 w-full" />
                  <Skeleton className="h-10 w-3/4" />
                </div>
              )}

              {timeline && timeline.length === 0 && (
                <p className="text-sm text-muted-foreground">
                  هنوز رویدادی برای این درخواست ثبت نشده.
                </p>
              )}

              {timeline && timeline.length > 0 && (
                <ol className="flex flex-col gap-3 border-e-2 border-border pe-4">
                  {timeline.map((entry) => (
                    <li key={`${entry.entry_type}-${entry.id}`} className="relative">
                      <span className="absolute top-1 -end-[21px] size-2 rounded-full bg-primary" />
                      {entry.entry_type === "history" ? (
                        <div className="flex flex-col gap-0.5">
                          <p className="text-sm">{describeHistoryEntry(entry)}</p>
                          <span className="text-xs text-muted-foreground">
                            {entry.user_username ?? "سامانه"} · {formatDate(entry.created_at)}
                          </span>
                        </div>
                      ) : (
                        <div className="flex flex-col gap-0.5 rounded-lg border bg-muted/40 p-2.5">
                          <p className="text-sm">{entry.text}</p>
                          <span className="text-xs text-muted-foreground">
                            یادداشت {entry.author_username ?? "—"} · {formatDate(entry.created_at)}
                          </span>
                        </div>
                      )}
                    </li>
                  ))}
                </ol>
              )}

              <div className="flex flex-col gap-1.5 border-t pt-4">
                <Label htmlFor="note">افزودن یادداشت داخلی</Label>
                <Textarea
                  id="note"
                  placeholder="یادداشتی برای همکاران (فقط برای اپراتور/ادمین قابل مشاهده است)…"
                  value={noteText}
                  onChange={(e) => setNoteText(e.target.value)}
                />
                <Button
                  size="sm"
                  className="w-fit gap-1.5"
                  disabled={!noteText.trim() || isAddingNote}
                  onClick={handleAddNote}
                >
                  {isAddingNote ? (
                    <Loader2 className="size-3.5 animate-spin" />
                  ) : (
                    <MessageSquarePlus className="size-3.5" />
                  )}
                  {isAddingNote ? "در حال ثبت…" : "ثبت یادداشت"}
                </Button>
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </main>
  );
}