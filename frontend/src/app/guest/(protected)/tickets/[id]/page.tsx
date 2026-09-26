"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight, CheckCircle2, Loader2, RotateCcw } from "lucide-react";

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
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { FormError } from "@/components/form-error";
import { RelativeTime } from "@/components/relative-time";
import { TicketPdfExportButton } from "@/components/ticket-pdf-export-button";
import { toast } from "@/hooks/use-toast";
import { useLocale } from "@/contexts/locale-context";
import { priorityMessageKey, statusMessageKey } from "@/lib/i18n";
import { StarDisplay, StarPicker } from "@/components/star-rating";
import { getTicketDetail, rateTicket, reopenTicket, ApiError } from "@/lib/api/client";
import type { Ticket } from "@/lib/api/types";
import { statusBadgeVariant, priorityBadgeVariant, priorityIcons } from "@/lib/ticket-labels";

/** Interactive 1-5 star picker, used before a rating has been submitted. */
export default function GuestTicketDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [ticket, setTicket] = useState<Ticket | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [ratingValue, setRatingValue] = useState(0);
  const [feedback, setFeedback] = useState("");
  const [isSubmittingRating, setIsSubmittingRating] = useState(false);

  const [isReopening, setIsReopening] = useState(false);
  const [isReopenDialogOpen, setIsReopenDialogOpen] = useState(false);
  const { t } = useLocale();

  const load = () => {
    // Deferred (not synchronous) so calling load() directly from a
    // useEffect body doesn't trip react-hooks/set-state-in-effect — see
    // operator/tickets/[id]/page.tsx for the full rationale.
    queueMicrotask(() => setError(null));
    getTicketDetail(id)
      .then(setTicket)
      .catch((err) => {
        setError(
          err instanceof ApiError && err.status === 404
            ? t("detail.notFound")
            : err instanceof ApiError
              ? err.message
              : t("detail.loadError")
        );
      });
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const handleSubmitRating = async () => {
    if (ratingValue === 0) return;
    setIsSubmittingRating(true);
    try {
      const updated = await rateTicket(id, ratingValue, feedback.trim());
      setTicket(updated);
      toast({
        title: t("detail.thanksTitle"),
        description: t("detail.thanksBody"),
        variant: "success",
      });
    } catch (err) {
      toast({
        title: t("detail.ratingError"),
        description: err instanceof ApiError ? err.message : t("common.retry"),
        variant: "destructive",
      });
    } finally {
      setIsSubmittingRating(false);
    }
  };

  const handleReopen = async () => {
    setIsReopening(true);
    try {
      const updated = await reopenTicket(id);
      setTicket(updated);
      setIsReopenDialogOpen(false);
      toast({
        title: t("detail.reopenedTitle"),
        description: t("detail.reopenedBody"),
        variant: "success",
      });
    } catch (err) {
      toast({
        title: t("detail.reopenError"),
        description: err instanceof ApiError ? err.message : t("common.retry"),
        variant: "destructive",
      });
    } finally {
      setIsReopening(false);
    }
  };

  return (
    <main className="mx-auto flex w-full max-w-lg flex-1 flex-col gap-4">
      <div className="flex items-center justify-between gap-2">
        <Button asChild variant="ghost" size="sm" className="w-fit gap-1.5">
          <Link href="/guest/tickets">
            <ArrowRight className="size-3.5 ltr:rotate-180" />
            {t("detail.backToList")}
          </Link>
        </Button>
        {ticket && <TicketPdfExportButton ticketId={ticket.id} />}
      </div>

      {!ticket && !error && (
        <Card>
          <CardHeader>
            <div className="flex items-start justify-between gap-2">
              <Skeleton className="h-5 w-40" />
              <Skeleton className="h-5 w-16" />
            </div>
            <Skeleton className="h-3.5 w-32" />
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <div className="flex gap-2">
              <Skeleton className="h-5 w-20" />
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

      {ticket && (() => {
        const PriorityIcon = priorityIcons[ticket.priority];
        return (
        <Card>
          <CardHeader>
            <div className="flex items-start justify-between gap-2">
              <CardTitle className="display-3">{ticket.title}</CardTitle>
              <Badge variant={statusBadgeVariant[ticket.status]}>
                {t(statusMessageKey(ticket.status))}
              </Badge>
            </div>
            <CardDescription>
              {ticket.department_name} · {ticket.category_name}
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            {ticket.merged_into && (
              <p className="border border-dashed px-3 py-2 text-sm text-muted-foreground">
                {t("detail.mergedInto", { id: ticket.merged_into })}{" "}
                <Link href={`/guest/tickets/${ticket.merged_into}`} className="text-primary underline">
                  {t("detail.openMerged", { id: ticket.merged_into })}
                </Link>
              </p>
            )}
            <div className="flex gap-2">
              <Badge variant={priorityBadgeVariant[ticket.priority]} className="gap-1">
                <PriorityIcon className="size-3" />
                {t("detail.priority", { priority: t(priorityMessageKey(ticket.priority)) })}
              </Badge>
            </div>

            <div className="flex flex-col gap-1">
              <span className="text-xs text-muted-foreground">{t("detail.description")}</span>
              <p className="text-sm">{ticket.description}</p>
            </div>

            {ticket.attachments.length > 0 && (
              <div className="flex flex-col gap-1.5">
                <span className="text-xs text-muted-foreground">{t("detail.attachments")}</span>
                <div className="flex flex-wrap gap-2">
                  {ticket.attachments.map((attachment) => (
                    <a
                      key={attachment.id}
                      href={attachment.image}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="block overflow-hidden rounded-md border"
                    >
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img
                        src={attachment.image}
                        alt={t("detail.attachmentAlt")}
                        className="size-20 object-cover"
                      />
                    </a>
                  ))}
                </div>
              </div>
            )}

            <div className="grid grid-cols-2 gap-3 text-xs text-muted-foreground">
              <span>
                {t("detail.created")} <RelativeTime iso={ticket.created_at} />
              </span>
              <span>
                {t("detail.updated")} <RelativeTime iso={ticket.updated_at} />
              </span>
            </div>

            {ticket.status === "RESOLVED" && ticket.resolution && (
              <div className="flex flex-col gap-1 rounded-lg border border-success/30 bg-success/10 p-3">
                <div className="flex items-center gap-1.5 text-sm font-medium text-success">
                  <CheckCircle2 className="size-4" />
                  {t("detail.resolution")}
                </div>
                <p className="text-sm">{ticket.resolution}</p>
                {ticket.resolved_at && (
                  <span className="text-xs text-muted-foreground">
                    {t("detail.resolvedAt")} <RelativeTime iso={ticket.resolved_at} />
                  </span>
                )}
              </div>
            )}
          </CardContent>
        </Card>
        );
      })()}

      {/* Stage 2.3 — rating + reopen, only once the ticket is RESOLVED */}
      {ticket && ticket.status === "RESOLVED" && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base font-medium">
              {ticket.guest_rating ? t("detail.yourRating") : t("detail.rateQuestion")}
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            {ticket.guest_rating ? (
              <div className="flex flex-col gap-1.5">
                <StarDisplay value={ticket.guest_rating} />
                {ticket.guest_feedback && (
                  <p className="text-sm text-muted-foreground">{ticket.guest_feedback}</p>
                )}
              </div>
            ) : (
              <div className="flex flex-col gap-3">
                <StarPicker value={ratingValue} onChange={setRatingValue} />
                <div className="flex flex-col gap-1.5">
                  <Label htmlFor="feedback">{t("detail.feedbackLabel")}</Label>
                  <Textarea
                    id="feedback"
                    value={feedback}
                    onChange={(e) => setFeedback(e.target.value)}
                    placeholder={t("detail.feedbackPlaceholder")}
                    rows={3}
                  />
                </div>
                <Button
                  className="w-fit gap-1.5"
                  disabled={ratingValue === 0 || isSubmittingRating}
                  onClick={handleSubmitRating}
                >
                  {isSubmittingRating && <Loader2 className="size-3.5 animate-spin" />}
                  {isSubmittingRating ? t("detail.submittingRating") : t("detail.submitRating")}
                </Button>
              </div>
            )}

            {ticket.can_reopen && (
              <div className="border-t pt-3">
                <Dialog open={isReopenDialogOpen} onOpenChange={setIsReopenDialogOpen}>
                  <DialogTrigger asChild>
                    <Button variant="outline" size="sm" className="w-fit gap-1.5">
                      <RotateCcw className="size-3.5" />
                      {t("detail.reopenButton")}
                    </Button>
                  </DialogTrigger>
                  <DialogContent>
                    <DialogHeader>
                      <DialogTitle>{t("detail.reopenTitle")}</DialogTitle>
                      <DialogDescription>{t("detail.reopenBody")}</DialogDescription>
                    </DialogHeader>
                    <DialogFooter>
                      <Button
                        variant="outline"
                        onClick={() => setIsReopenDialogOpen(false)}
                        disabled={isReopening}
                      >
                        {t("common.cancel")}
                      </Button>
                      <Button
                        className="gap-1.5"
                        onClick={handleReopen}
                        disabled={isReopening}
                      >
                        {isReopening && <Loader2 className="size-3.5 animate-spin" />}
                        {isReopening ? t("detail.reopening") : t("detail.reopenConfirm")}
                      </Button>
                    </DialogFooter>
                  </DialogContent>
                </Dialog>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </main>
  );
}
