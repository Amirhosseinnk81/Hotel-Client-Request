"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ChevronLeft, Inbox, UserCheck2 } from "lucide-react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { FormError } from "@/components/form-error";
import { getOperatorTickets, ApiError } from "@/lib/api/client";
import { useDebouncedValue } from "@/hooks/use-debounced-value";
import type { Ticket, TicketPriority, TicketStatus } from "@/lib/api/types";
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
  }).format(new Date(iso));
}

const statusFilterOptions: { value: TicketStatus | "ALL"; label: string }[] = [
  { value: "ALL", label: "همه‌ی وضعیت‌ها" },
  { value: "OPEN", label: statusLabels.OPEN },
  { value: "IN_PROGRESS", label: statusLabels.IN_PROGRESS },
  { value: "RESOLVED", label: statusLabels.RESOLVED },
  { value: "CANCELLED", label: statusLabels.CANCELLED },
];

const priorityFilterOptions: { value: TicketPriority | "ALL"; label: string }[] = [
  { value: "ALL", label: "همه‌ی اولویت‌ها" },
  { value: "LOW", label: priorityLabels.LOW },
  { value: "NORMAL", label: priorityLabels.NORMAL },
  { value: "HIGH", label: priorityLabels.HIGH },
  { value: "URGENT", label: priorityLabels.URGENT },
];

export default function OperatorHomePage() {
  const [tickets, setTickets] = useState<Ticket[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<TicketStatus | "ALL">("ALL");
  const [priorityFilter, setPriorityFilter] = useState<TicketPriority | "ALL">("ALL");
  const [searchInput, setSearchInput] = useState("");
  const debouncedSearch = useDebouncedValue(searchInput, 400);

  useEffect(() => {
    let cancelled = false;
    setError(null);

    getOperatorTickets({
      status: statusFilter === "ALL" ? undefined : statusFilter,
      priority: priorityFilter === "ALL" ? undefined : priorityFilter,
      search: debouncedSearch || undefined,
    })
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
  }, [statusFilter, priorityFilter, debouncedSearch]);

  return (
    <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-4">
      <div>
        <h1 className="text-xl font-semibold">درخواست‌های واحد شما</h1>
        <p className="text-sm text-muted-foreground">
          مدیریت درخواست‌های ثبت‌شده توسط مهمانان برای واحد شما.
        </p>
      </div>

      <div className="flex flex-col gap-3 sm:flex-row">
        <Input
          placeholder="جستجو در عنوان یا شماره اتاق…"
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

      <Select
        value={priorityFilter}
        onValueChange={(v) => setPriorityFilter(v as TicketPriority | "ALL")}
      >
        <SelectTrigger className="sm:max-w-48">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {priorityFilterOptions.map((opt) => (
            <SelectItem key={opt.value} value={opt.value}>
              {opt.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {!tickets && !error && (
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

      {tickets && tickets.length === 0 && (
        <Card>
          <CardContent className="flex flex-col items-center gap-2 pt-6 text-center text-sm text-muted-foreground">
            <Inbox className="size-6" />
            درخواستی با این فیلترها یافت نشد.
          </CardContent>
        </Card>
      )}

      {tickets && tickets.length > 0 && (
        <div className="flex flex-col gap-3">
          {tickets.map((ticket) => (
            <Link key={ticket.id} href={`/operator/tickets/${ticket.id}`}>
              <Card className="transition-colors hover:bg-secondary/40">
                <CardHeader className="flex-row items-start justify-between gap-2 space-y-0">
                  <div className="flex flex-col gap-1">
                    <CardTitle className="text-base">{ticket.title}</CardTitle>
                    <CardDescription>
                      اتاق {ticket.room_number} · {ticket.category_name} ·{" "}
                      {formatDate(ticket.created_at)}
                    </CardDescription>
                  </div>
                  <ChevronLeft className="mt-1 size-4 shrink-0 text-muted-foreground" />
                </CardHeader>
                <CardContent className="flex flex-wrap items-center gap-2">
                  <Badge variant={statusBadgeVariant[ticket.status]}>
                    {statusLabels[ticket.status]}
                  </Badge>
                  <Badge variant={priorityBadgeVariant[ticket.priority]}>
                    {priorityLabels[ticket.priority]}
                  </Badge>
                  <span className="flex items-center gap-1 text-xs text-muted-foreground">
                    <UserCheck2 className="size-3.5" />
                    {ticket.assigned_to_username ?? "اختصاص‌نیافته"}
                  </span>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </main>
  );
}