"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight, CheckCircle2 } from "lucide-react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { FormError } from "@/components/form-error";
import { getTicketDetail, ApiError } from "@/lib/api/client";
import type { Ticket } from "@/lib/api/types";
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

export default function GuestTicketDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [ticket, setTicket] = useState<Ticket | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    getTicketDetail(id)
      .then((data) => {
        if (!cancelled) setTicket(data);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(
            err instanceof ApiError && err.status === 404
              ? "چنین درخواستی یافت نشد."
              : err instanceof ApiError
                ? err.message
                : "خطا در دریافت جزئیات درخواست."
          );
        }
      });

    return () => {
      cancelled = true;
    };
  }, [id]);

  return (
    <main className="mx-auto flex w-full max-w-lg flex-1 flex-col gap-4">
      <Button asChild variant="ghost" size="sm" className="w-fit gap-1.5">
        <Link href="/guest/tickets">
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
        <Card>
          <CardHeader>
            <div className="flex items-start justify-between gap-2">
              <CardTitle className="text-lg">{ticket.title}</CardTitle>
              <Badge variant={statusBadgeVariant[ticket.status]}>
                {statusLabels[ticket.status]}
              </Badge>
            </div>
            <CardDescription>
              {ticket.department_name} · {ticket.category_name}
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <div className="flex gap-2">
              <Badge variant={priorityBadgeVariant[ticket.priority]}>
                اولویت: {priorityLabels[ticket.priority]}
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
      )}
    </main>
  );
}
