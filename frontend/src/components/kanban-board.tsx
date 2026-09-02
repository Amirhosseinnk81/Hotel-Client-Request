"use client";

import { useState } from "react";
import Link from "next/link";
import { AlertTriangle } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ResolveTicketDialog } from "@/components/resolve-ticket-dialog";
import { toast } from "@/hooks/use-toast";
import { updateOperatorTicket, ApiError } from "@/lib/api/client";
import {
  allowedNextStatuses,
  statusLabels,
  priorityBadgeVariant,
  priorityLabels,
} from "@/lib/ticket-labels";
import type { Ticket, TicketStatus } from "@/lib/api/types";

/**
 * Deliberately only these three — CANCELLED isn't a Kanban column (the
 * spec calls for exactly OPEN/IN_PROGRESS/RESOLVED); cancelling still
 * happens from the ticket detail page.
 */
const COLUMNS: TicketStatus[] = ["OPEN", "IN_PROGRESS", "RESOLVED"];

export function KanbanBoard({
  tickets,
  onTicketChange,
}: {
  tickets: Ticket[];
  onTicketChange: (updated: Ticket) => void;
}) {
  const [draggedId, setDraggedId] = useState<number | null>(null);
  const [dragOverColumn, setDragOverColumn] = useState<TicketStatus | null>(null);
  const [resolveDialogTicketId, setResolveDialogTicketId] = useState<number | null>(null);

  const ticketsInColumn = (column: TicketStatus) =>
    tickets.filter((ticket) => ticket.status === column);

  const handleDrop = async (targetStatus: TicketStatus) => {
    setDragOverColumn(null);
    const ticket = tickets.find((t) => t.id === draggedId);
    setDraggedId(null);
    if (!ticket || ticket.status === targetStatus) return;

    // Same rule the detail page's status Select enforces — see
    // lib/ticket-labels.ts for why this is imported, not redefined here.
    if (!allowedNextStatuses[ticket.status].includes(targetStatus)) {
      toast({
        title: "این جابه‌جایی مجاز نیست",
        description: `درخواست از «${statusLabels[ticket.status]}» نمی‌تواند مستقیم به «${statusLabels[targetStatus]}» برود.`,
        variant: "destructive",
      });
      return;
    }

    // RESOLVED needs a resolution text (and optionally a photo) — can't
    // just PATCH the status directly like the other transitions.
    if (targetStatus === "RESOLVED") {
      setResolveDialogTicketId(ticket.id);
      return;
    }

    try {
      const updated = await updateOperatorTicket(ticket.id, { status: targetStatus });
      onTicketChange(updated);
      toast({
        title: "وضعیت به‌روزرسانی شد",
        description: `وضعیت به «${statusLabels[updated.status]}» تغییر کرد.`,
        variant: "success",
      });
    } catch (err) {
      toast({
        title: "خطا در تغییر وضعیت",
        description: err instanceof ApiError ? err.message : "لطفاً دوباره تلاش کنید.",
        variant: "destructive",
      });
    }
  };

  return (
    <>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        {COLUMNS.map((column) => (
          <div
            key={column}
            onDragOver={(e) => {
              e.preventDefault();
              if (dragOverColumn !== column) setDragOverColumn(column);
            }}
            onDragLeave={() => setDragOverColumn((current) => (current === column ? null : current))}
            onDrop={(e) => {
              e.preventDefault();
              void handleDrop(column);
            }}
            className={
              "flex flex-col gap-2 rounded-lg border p-2 transition-colors " +
              (dragOverColumn === column ? "border-primary bg-secondary/40" : "bg-secondary/10")
            }
          >
            <div className="flex items-center justify-between px-1">
              <h3 className="text-sm font-medium">{statusLabels[column]}</h3>
              <span className="text-xs text-muted-foreground">
                {ticketsInColumn(column).length}
              </span>
            </div>

            <div className="flex min-h-24 flex-col gap-2">
              {ticketsInColumn(column).map((ticket) => (
                <div
                  key={ticket.id}
                  draggable
                  onDragStart={() => setDraggedId(ticket.id)}
                  onDragEnd={() => setDraggedId(null)}
                >
                  <Link href={`/operator/tickets/${ticket.id}`}>
                    <Card
                      className={
                        "cursor-grab gap-2 py-3 transition-colors hover:bg-secondary/40 active:cursor-grabbing " +
                        (ticket.is_overdue ? "border-destructive/60 bg-destructive/5" : "")
                      }
                    >
                      <CardHeader className="px-3">
                        <CardTitle className="text-sm leading-snug">{ticket.title}</CardTitle>
                      </CardHeader>
                      <CardContent className="flex flex-wrap items-center gap-1.5 px-3">
                        <Badge
                          variant={priorityBadgeVariant[ticket.priority]}
                          className="text-xs"
                        >
                          {priorityLabels[ticket.priority]}
                        </Badge>
                        {ticket.is_overdue && (
                          <Badge variant="destructive" className="gap-1 text-xs">
                            <AlertTriangle className="size-3" />
                            معوق
                          </Badge>
                        )}
                      </CardContent>
                    </Card>
                  </Link>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      {resolveDialogTicketId !== null && (
        <ResolveTicketDialog
          ticketId={resolveDialogTicketId}
          open={resolveDialogTicketId !== null}
          onOpenChange={(open) => {
            if (!open) setResolveDialogTicketId(null);
          }}
          onResolved={(updated) => {
            onTicketChange(updated);
            setResolveDialogTicketId(null);
          }}
        />
      )}
    </>
  );
}
