"use client";

import { useState } from "react";
import { GitMerge, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { RelativeTime } from "@/components/relative-time";
import { toast } from "@/hooks/use-toast";
import { ApiError, getMergeCandidates, mergeTicket } from "@/lib/api/client";
import type { Ticket } from "@/lib/api/types";
import { statusLabels } from "@/lib/ticket-labels";

/**
 * Supervisor only: fold this OPEN ticket into another open ticket of the
 * same guest as a duplicate (inspired by Odoo Helpdesk's merge). The
 * backend (services.merge_tickets) enforces the rules; this lists the
 * candidates it would accept and confirms, since the duplicate is
 * cancelled and that can't be undone.
 */
export function MergeTicketDialog({
  ticket,
  onMerged,
}: {
  ticket: Ticket;
  onMerged: (kept: Ticket) => void;
}) {
  const [open, setOpen] = useState(false);
  const [candidates, setCandidates] = useState<Ticket[] | null>(null);
  const [selected, setSelected] = useState<number | null>(null);
  const [isMerging, setIsMerging] = useState(false);

  const handleOpenChange = (next: boolean) => {
    setOpen(next);
    if (!next) return;
    setCandidates(null);
    setSelected(null);
    getMergeCandidates(ticket.id)
      .then(setCandidates)
      .catch(() => setCandidates([]));
  };

  const handleMerge = async () => {
    if (selected === null) return;
    setIsMerging(true);
    try {
      const kept = await mergeTicket(ticket.id, selected);
      toast({
        title: "ادغام شد",
        description: `این درخواست با #${kept.id} ادغام و لغو شد.`,
        variant: "success",
      });
      setOpen(false);
      onMerged(kept);
    } catch (err) {
      toast({
        title: "ادغام نشد",
        description: err instanceof ApiError ? err.message : "لطفاً دوباره تلاش کنید.",
        variant: "destructive",
      });
    } finally {
      setIsMerging(false);
    }
  };

  return (
    <>
      <Button variant="outline" size="sm" className="w-fit gap-1.5" onClick={() => handleOpenChange(true)}>
        <GitMerge className="size-3.5" />
        ادغام با درخواست تکراری
      </Button>
      <Dialog open={open} onOpenChange={handleOpenChange}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>ادغام درخواست تکراری</DialogTitle>
            <DialogDescription>
              این درخواست لغو می‌شود و توضیح و عکس‌هایش به درخواستی که انتخاب می‌کنید منتقل می‌شود. این
              کار برگشت‌پذیر نیست.
            </DialogDescription>
          </DialogHeader>

          <div className="flex flex-col gap-2">
            {candidates === null ? (
              <Skeleton className="h-14 w-full" />
            ) : candidates.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                این مهمان درخواست باز دیگری در این واحد ندارد.
              </p>
            ) : (
              candidates.map((candidate) => (
                <label
                  key={candidate.id}
                  className={`flex cursor-pointer items-start gap-3 border p-3 text-sm transition-colors ${
                    selected === candidate.id ? "border-primary bg-secondary/50" : "hover:bg-secondary/30"
                  }`}
                >
                  <input
                    type="radio"
                    name="merge-target"
                    className="mt-1"
                    checked={selected === candidate.id}
                    onChange={() => setSelected(candidate.id)}
                  />
                  <span className="flex flex-col gap-0.5">
                    <span>
                      #{candidate.id} — {candidate.title}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {statusLabels[candidate.status]} · {candidate.category_name} ·{" "}
                      <RelativeTime iso={candidate.created_at} />
                    </span>
                  </span>
                </label>
              ))
            )}
          </div>

          <DialogFooter>
            <Button variant="ghost" onClick={() => setOpen(false)}>
              انصراف
            </Button>
            <Button disabled={selected === null || isMerging} onClick={handleMerge} className="gap-1.5">
              {isMerging && <Loader2 className="size-3.5 animate-spin" />}
              ادغام
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
