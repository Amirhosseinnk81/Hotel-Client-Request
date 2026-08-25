"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight, CheckCircle2, UserPlus } from "lucide-react";

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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { FormError } from "@/components/form-error";
import {
  assignTicketToSelf,
  getOperatorTicketDetail,
  updateOperatorTicket,
  ApiError,
} from "@/lib/api/client";
import { decodeAccessToken, getStoredTokens } from "@/lib/api/tokens";
import type { Ticket, TicketStatus } from "@/lib/api/types";
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

/** Business rule: OPEN → IN_PROGRESS → RESOLVED, or OPEN/IN_PROGRESS → CANCELLED. */
const allowedNextStatuses: Record<TicketStatus, TicketStatus[]> = {
  OPEN: ["IN_PROGRESS", "CANCELLED"],
  IN_PROGRESS: ["RESOLVED", "CANCELLED"],
  RESOLVED: [],
  CANCELLED: [],
};

export default function OperatorTicketDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);

  const [ticket, setTicket] = useState<Ticket | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [isAssigning, setIsAssigning] = useState(false);
  const [assignError, setAssignError] = useState<string | null>(null);

  const [targetStatus, setTargetStatus] = useState<TicketStatus | "">("");
  const [resolution, setResolution] = useState("");
  const [isUpdating, setIsUpdating] = useState(false);
  const [updateError, setUpdateError] = useState<string | null>(null);

  const currentUserId = decodeAccessToken(getStoredTokens()?.access ?? "")?.user_id ?? null;

  const load = () => {
    setError(null);
    getOperatorTicketDetail(id)
      .then((data) => {
        setTicket(data);
        setTargetStatus("");
        setResolution("");
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const handleAssign = async () => {
    setIsAssigning(true);
    setAssignError(null);
    try {
      const updated = await assignTicketToSelf(id);
      setTicket(updated);
    } catch (err) {
      setAssignError(err instanceof ApiError ? err.message : "خطا در اختصاص درخواست.");
    } finally {
      setIsAssigning(false);
    }
  };

  const handleUpdateStatus = async () => {
    if (!targetStatus) return;
    setIsUpdating(true);
    setUpdateError(null);
    try {
      const updated = await updateOperatorTicket(id, {
        status: targetStatus,
        ...(targetStatus === "RESOLVED" ? { resolution } : {}),
      });
      setTicket(updated);
      setTargetStatus("");
      setResolution("");
    } catch (err) {
      setUpdateError(err instanceof ApiError ? err.message : "خطا در تغییر وضعیت.");
    } finally {
      setIsUpdating(false);
    }
  };

  const options = ticket ? allowedNextStatuses[ticket.status] : [];
  const isAssignedToMe = ticket?.assigned_to !== null && ticket?.assigned_to === currentUserId;
  const needsResolution = targetStatus === "RESOLVED";
  const canSubmitStatus =
    !!targetStatus && (!needsResolution || resolution.trim().length > 0);

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
          <CardContent className="pt-6 text-sm text-muted-foreground">
            در حال بارگذاری…
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

          {!ticket.assigned_to && (
            <Card>
              <CardContent className="flex items-center justify-between gap-3 pt-6">
                <p className="text-sm text-muted-foreground">
                  این درخواست هنوز به کسی اختصاص داده نشده.
                </p>
                <Button
                  size="sm"
                  className="gap-1.5"
                  disabled={isAssigning}
                  onClick={handleAssign}
                >
                  <UserPlus className="size-3.5" />
                  {isAssigning ? "در حال اختصاص…" : "اختصاص به خودم"}
                </Button>
              </CardContent>
              {assignError && (
                <CardContent className="pt-0">
                  <FormError message={assignError} />
                </CardContent>
              )}
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

                <FormError message={updateError} />

                <Button
                  className="w-fit"
                  disabled={!canSubmitStatus || isUpdating}
                  onClick={handleUpdateStatus}
                >
                  {isUpdating ? "در حال ثبت…" : "ثبت تغییر وضعیت"}
                </Button>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </main>
  );
}