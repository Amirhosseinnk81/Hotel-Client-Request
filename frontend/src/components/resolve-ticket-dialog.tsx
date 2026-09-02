"use client";

import { useState } from "react";
import { ImagePlus, Loader2 } from "lucide-react";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { toast } from "@/hooks/use-toast";
import {
  addOperatorTicketAttachment,
  updateOperatorTicket,
  ApiError,
} from "@/lib/api/client";
import type { Ticket } from "@/lib/api/types";

/**
 * Self-contained "mark as RESOLVED" dialog: captures the required
 * resolution text and an optional photo, then calls the same
 * updateOperatorTicket + addOperatorTicketAttachment pair the ticket
 * detail page's inline form uses. Built for the Kanban board (Stage
 * 2.10), where a column has no room for an inline form — but it's a
 * standalone component precisely so the detail page (or anywhere else)
 * can switch to it later instead of duplicating this flow again.
 */
export function ResolveTicketDialog({
  ticketId,
  open,
  onOpenChange,
  onResolved,
}: {
  ticketId: number;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onResolved: (updated: Ticket) => void;
}) {
  const [resolution, setResolution] = useState("");
  const [attachment, setAttachment] = useState<File | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const reset = () => {
    setResolution("");
    setAttachment(null);
  };

  const handleOpenChange = (next: boolean) => {
    if (!next) reset();
    onOpenChange(next);
  };

  const handleConfirm = async () => {
    if (!resolution.trim()) return;
    setIsSubmitting(true);
    try {
      const updated = await updateOperatorTicket(ticketId, {
        status: "RESOLVED",
        resolution: resolution.trim(),
      });

      let finalTicket = updated;
      if (attachment) {
        try {
          const uploaded = await addOperatorTicketAttachment(ticketId, attachment);
          finalTicket = { ...updated, attachments: [...updated.attachments, uploaded] };
        } catch (attachmentErr) {
          toast({
            title: "وضعیت ثبت شد، ولی عکس پیوست نشد",
            description:
              attachmentErr instanceof ApiError ? attachmentErr.message : "خطا در آپلود تصویر.",
            variant: "destructive",
          });
        }
      }

      toast({
        title: "درخواست حل شد",
        description: "وضعیت به «حل‌شده» تغییر کرد.",
        variant: "success",
      });
      onResolved(finalTicket);
      reset();
      onOpenChange(false);
    } catch (err) {
      toast({
        title: "خطا در ثبت نتیجه",
        description: err instanceof ApiError ? err.message : "لطفاً دوباره تلاش کنید.",
        variant: "destructive",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>ثبت نتیجهٔ رسیدگی</DialogTitle>
          <DialogDescription>
            برای علامت‌گذاری این درخواست به‌عنوان حل‌شده، توضیح دهید چه اقدامی انجام شد.
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-3">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="kanban-resolution">نتیجهٔ رسیدگی</Label>
            <Textarea
              id="kanban-resolution"
              placeholder="توضیح دهید که چه اقدامی انجام شد…"
              value={resolution}
              onChange={(e) => setResolution(e.target.value)}
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="kanban-resolution-attachment">عکس نتیجه (اختیاری)</Label>
            <label
              htmlFor="kanban-resolution-attachment"
              className="flex cursor-pointer items-center gap-2 rounded-md border border-dashed px-3 py-2 text-sm text-muted-foreground transition-colors hover:bg-secondary/40"
            >
              <ImagePlus className="size-4 shrink-0" />
              {attachment ? attachment.name : "انتخاب تصویر…"}
            </label>
            <input
              id="kanban-resolution-attachment"
              type="file"
              accept="image/*"
              className="sr-only"
              onChange={(e) => setAttachment(e.target.files?.[0] ?? null)}
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => handleOpenChange(false)} disabled={isSubmitting}>
            انصراف
          </Button>
          <Button
            className="gap-1.5"
            disabled={!resolution.trim() || isSubmitting}
            onClick={handleConfirm}
          >
            {isSubmitting && <Loader2 className="size-3.5 animate-spin" />}
            {isSubmitting ? "در حال ثبت…" : "ثبت و حل کن"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
