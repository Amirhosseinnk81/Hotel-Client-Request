"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ArrowRight, ChevronLeft, Inbox } from "lucide-react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { FormError } from "@/components/form-error";
import { Skeleton } from "@/components/ui/skeleton";
import { RelativeTime } from "@/components/relative-time";
import { getTickets, ApiError } from "@/lib/api/client";
import { useDebouncedValue } from "@/hooks/use-debounced-value";
import type { Ticket, TicketStatus } from "@/lib/api/types";
import {
  statusLabels,
  statusBadgeVariant,
  priorityLabels,
  priorityBadgeVariant,
  priorityIcons,
} from "@/lib/ticket-labels";

const statusFilterOptions: { value: TicketStatus | "ALL"; label: string }[] = [
  { value: "ALL", label: "همه‌ی وضعیت‌ها" },
  { value: "OPEN", label: statusLabels.OPEN },
  { value: "IN_PROGRESS", label: statusLabels.IN_PROGRESS },
  { value: "RESOLVED", label: statusLabels.RESOLVED },
  { value: "CANCELLED", label: statusLabels.CANCELLED },
];

export default function GuestTicketsPage() {
  const [tickets, setTickets] = useState<Ticket[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [searchInput, setSearchInput] = useState("");
  const [statusFilter, setStatusFilter] = useState<TicketStatus | "ALL">("ALL");
  const debouncedSearch = useDebouncedValue(searchInput, 400);

  useEffect(() => {
    let cancelled = false;
    // Deferred (not called synchronously in the effect body) to satisfy
    // react-hooks/set-state-in-effect — see operator/tickets/[id]/page.tsx
    // for the full rationale.
    queueMicrotask(() => {
      if (!cancelled) setError(null);
    });

    getTickets(debouncedSearch || undefined)
      .then((data) => {
        if (!cancelled) setTickets(data);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : "خطا در دریافت درخواست‌ها.");
        }
      });

    return () => {
      cancelled = true;
    };
  }, [debouncedSearch]);

  // پارامتر status توی API لیست تیکت‌های مهمان پشتیبانی نمی‌شه،
  // پس فیلتر وضعیت رو روی همون نتایج دریافتی سمت کلاینت اعمال می‌کنیم.
  const filteredTickets = useMemo(() => {
    if (!tickets) return tickets;
    if (statusFilter === "ALL") return tickets;
    return tickets.filter((t) => t.status === statusFilter);
  }, [tickets, statusFilter]);

  return (
    <main className="mx-auto flex w-full max-w-lg flex-1 flex-col gap-4">
      <Button asChild variant="ghost" size="sm" className="w-fit gap-1.5">
        <Link href="/guest">
          <ArrowRight className="size-3.5" />
          بازگشت
        </Link>
      </Button>

      <div>
        <h1 className="display-2">درخواست‌های من</h1>
        <p className="text-sm text-muted-foreground">
          لیست درخواست‌هایی که تاکنون ثبت کرده‌اید.
        </p>
      </div>

      <div className="flex flex-col gap-3 sm:flex-row">
        <Input
          placeholder="جستجو در عنوان یا توضیحات…"
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          className="sm:max-w-xs"
        />
        <Select
          value={statusFilter}
          onValueChange={(v) => setStatusFilter(v as TicketStatus | "ALL")}
        >
          <SelectTrigger className="sm:max-w-48">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {statusFilterOptions.map((opt) => (
              <SelectItem key={opt.value} value={opt.value}>
                {opt.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {!tickets && !error && (
        <div className="flex flex-col gap-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Card key={i}>
              <CardHeader className="flex-row items-start justify-between gap-2 space-y-0">
                <div className="flex flex-1 flex-col gap-2">
                  <Skeleton className="h-4 w-2/3" />
                  <Skeleton className="h-3 w-1/2" />
                </div>
              </CardHeader>
              <CardContent className="flex gap-2">
                <Skeleton className="h-5 w-14" />
                <Skeleton className="h-5 w-14" />
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {error && (
        <Card>
          <CardContent className="pt-6">
            <FormError message={error} />
          </CardContent>
        </Card>
      )}

      {filteredTickets && filteredTickets.length === 0 && (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 pt-6 pb-8 text-center">
            <Inbox className="size-8 text-muted-foreground/60" />
            <div className="flex flex-col gap-1">
              <p className="text-sm font-medium">
                {tickets && tickets.length > 0 ? "موردی یافت نشد" : "هنوز درخواستی ندارید"}
              </p>
              <p className="text-sm text-muted-foreground">
                {tickets && tickets.length > 0
                  ? "با این فیلتر یا عبارت جست‌وجو درخواستی پیدا نشد."
                  : "با ثبت اولین درخواست، اینجا نمایش داده می‌شود."}
              </p>
            </div>
            {tickets && tickets.length > 0 ? (
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setStatusFilter("ALL");
                  setSearchInput("");
                }}
              >
                پاک‌کردن فیلترها
              </Button>
            ) : (
              <Button asChild size="sm" className="gap-1.5">
                <Link href="/guest/tickets/new">ثبت درخواست جدید</Link>
              </Button>
            )}
          </CardContent>
        </Card>
      )}

      {filteredTickets && filteredTickets.length > 0 && (
        <div className="flex flex-col gap-3">
          {filteredTickets.map((ticket) => {
            const PriorityIcon = priorityIcons[ticket.priority];
            return (
              <Link
                key={ticket.id}
                href={`/guest/tickets/${ticket.id}`}
                className="rounded-xl outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
              >
                <Card className="transition-colors hover:bg-secondary/40">
                  <CardHeader className="flex-row items-start justify-between gap-2 space-y-0">
                    <div className="flex flex-col gap-1">
                      <CardTitle className="text-base font-medium">{ticket.title}</CardTitle>
                      <CardDescription>
                        {ticket.department_name} · {ticket.category_name} ·{" "}
                        <RelativeTime iso={ticket.created_at} />
                      </CardDescription>
                    </div>
                    <ChevronLeft className="mt-1 size-4 shrink-0 text-muted-foreground" />
                  </CardHeader>
                  <CardContent className="flex gap-2">
                    <Badge variant={statusBadgeVariant[ticket.status]}>
                      {statusLabels[ticket.status]}
                    </Badge>
                    <Badge variant={priorityBadgeVariant[ticket.priority]} className="gap-1">
                      <PriorityIcon className="size-3" />
                      {priorityLabels[ticket.priority]}
                    </Badge>
                  </CardContent>
                </Card>
              </Link>
            );
          })}
        </div>
      )}
    </main>
  );
}