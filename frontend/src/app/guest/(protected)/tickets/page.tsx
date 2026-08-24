"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ChevronLeft, Inbox } from "lucide-react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { FormError } from "@/components/form-error";
import { getTickets, ApiError } from "@/lib/api/client";
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
  }).format(new Date(iso));
}

export default function GuestTicketsPage() {
  const [tickets, setTickets] = useState<Ticket[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    getTickets()
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
  }, []);

  return (
    <main className="mx-auto flex w-full max-w-lg flex-1 flex-col gap-4">
      <div>
        <h1 className="text-xl font-semibold">درخواست‌های من</h1>
        <p className="text-sm text-muted-foreground">
          لیست درخواست‌هایی که تاکنون ثبت کرده‌اید.
        </p>
      </div>

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
            هنوز درخواستی ثبت نکرده‌اید.
          </CardContent>
        </Card>
      )}

      {tickets && tickets.length > 0 && (
        <div className="flex flex-col gap-3">
          {tickets.map((ticket) => (
            <Link key={ticket.id} href={`/guest/tickets/${ticket.id}`}>
              <Card className="transition-colors hover:bg-secondary/40">
                <CardHeader className="flex-row items-start justify-between gap-2 space-y-0">
                  <div className="flex flex-col gap-1">
                    <CardTitle className="text-base">{ticket.title}</CardTitle>
                    <CardDescription>
                      {ticket.department_name} · {ticket.category_name} ·{" "}
                      {formatDate(ticket.created_at)}
                    </CardDescription>
                  </div>
                  <ChevronLeft className="mt-1 size-4 shrink-0 text-muted-foreground" />
                </CardHeader>
                <CardContent className="flex gap-2">
                  <Badge variant={statusBadgeVariant[ticket.status]}>
                    {statusLabels[ticket.status]}
                  </Badge>
                  <Badge variant={priorityBadgeVariant[ticket.priority]}>
                    {priorityLabels[ticket.priority]}
                  </Badge>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </main>
  );
}
