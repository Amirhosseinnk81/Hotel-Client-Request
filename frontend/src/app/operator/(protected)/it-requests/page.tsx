"use client";

import { type ComponentType, useCallback, useEffect, useState } from "react";
import { ImagePlus, Loader2, Send, Sparkles, Wrench } from "lucide-react";
import * as LucideIcons from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { FormError } from "@/components/form-error";
import { RelativeTime } from "@/components/relative-time";
import { StarDisplay, StarPicker } from "@/components/star-rating";
import { PRIORITY_VARIANT } from "@/components/it-ops/today-panel";
import { toast } from "@/hooks/use-toast";
import {
  ApiError,
  addItRequestAttachment,
  createOutgoingItRequest,
  getItRequestTemplates,
  getOutgoingItRequests,
  rateItRequest,
} from "@/lib/api/client";
import type {
  ITPriority,
  ITRequestStatus,
  ITRequestTemplate,
  OutgoingITRequest,
} from "@/lib/api/types";
import { itPriorityLabels, itRequestStatusLabels } from "@/lib/it-ops";

const STATUS_VARIANT: Record<ITRequestStatus, "secondary" | "warning" | "success" | "destructive"> = {
  PENDING: "secondary",
  IN_PROGRESS: "warning",
  COMPLETED: "success",
  REJECTED: "destructive",
};

const PRIORITIES: ITPriority[] = ["LOW", "MEDIUM", "HIGH", "CRITICAL"];

/** Renders an ITRequestTemplate.icon (a lucide-react name) with a safe fallback. */
function TemplateIcon({ name }: { name: string }) {
  const Icon = (LucideIcons as unknown as Record<string, ComponentType<{ className?: string }>>)[
    name
  ];
  const Resolved = Icon ?? Wrench;
  return <Resolved className="size-5" />;
}

/**
 * «درخواست از IT» — how any department asks IT for something (a printer,
 * network access, a new PC) from its own panel, and follows it. Backed by
 * /it-ops/outgoing-requests/: the server fixes the department and
 * requester from the logged-in operator and only ever shows this
 * department's own requests. Status and assignee are IT's to change.
 *
 * Three things mirror the guest side deliberately, because the job is the
 * same one seen from the other end: one-click templates so nobody stares
 * at an empty box, a photo of the problem, and — once IT is finished — a
 * score and a comment, which is the only feedback an internal team
 * otherwise never gets.
 */
export default function ITRequestsPage() {
  const [requests, setRequests] = useState<OutgoingITRequest[] | null>(null);
  const [templates, setTemplates] = useState<ITRequestTemplate[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState<ITPriority>("MEDIUM");
  const [photo, setPhoto] = useState<File | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Which request's feedback box is open, and what is in it.
  const [ratingFor, setRatingFor] = useState<number | null>(null);
  const [rating, setRating] = useState(0);
  const [feedback, setFeedback] = useState("");
  const [isRating, setIsRating] = useState(false);

  const load = useCallback(() => {
    getOutgoingItRequests()
      .then((rows) => {
        setRequests(rows);
        setLoadError(null);
      })
      .catch((err) =>
        setLoadError(err instanceof ApiError ? err.message : "خطا در دریافت درخواست‌ها.")
      );
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    // A missing template list is not worth an error on screen: the form
    // works perfectly well without the shortcuts.
    getItRequestTemplates()
      .then(setTemplates)
      .catch(() => setTemplates([]));
  }, []);

  const applyTemplate = (template: ITRequestTemplate) => {
    setTitle(template.title);
    setDescription(template.description);
    setPriority(template.priority);
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!title.trim()) return;
    setIsSubmitting(true);
    try {
      const created = await createOutgoingItRequest({
        title: title.trim(),
        description: description.trim(),
        priority,
      });

      if (photo) {
        try {
          await addItRequestAttachment(created.id, photo);
        } catch (photoErr) {
          // The request itself went through — don't lose it over a photo.
          toast({
            title: "عکس پیوست نشد",
            description:
              photoErr instanceof ApiError ? photoErr.message : "درخواست ثبت شد، ولی عکس بالا نرفت.",
            variant: "destructive",
          });
        }
      }

      toast({
        title: "درخواست به IT رفت",
        description: `«${created.title}» ثبت شد؛ وضعیتش را همین‌جا دنبال کنید.`,
        variant: "success",
      });
      setTitle("");
      setDescription("");
      setPriority("MEDIUM");
      setPhoto(null);
      load();
    } catch (err) {
      toast({
        title: "ثبت نشد",
        description: err instanceof ApiError ? err.message : "لطفاً دوباره تلاش کنید.",
        variant: "destructive",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const openRating = (request: OutgoingITRequest) => {
    setRatingFor(request.id);
    setRating(0);
    setFeedback("");
  };

  const submitRating = async (requestId: number) => {
    if (rating < 1) return;
    setIsRating(true);
    try {
      await rateItRequest(requestId, rating, feedback.trim());
      toast({ title: "ممنون از بازخوردتان", variant: "success" });
      setRatingFor(null);
      load();
    } catch (err) {
      toast({
        title: "بازخورد ثبت نشد",
        description: err instanceof ApiError ? err.message : "لطفاً دوباره تلاش کنید.",
        variant: "destructive",
      });
    } finally {
      setIsRating(false);
    }
  };

  return (
    <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-8">
      <header className="flex flex-col gap-1">
        <p className="label-eyebrow">واحد فناوری اطلاعات</p>
        <h1 className="display-2 rule-accent">درخواست از IT</h1>
        <p className="pt-2 text-sm text-muted-foreground">
          مشکل یا نیاز فنی واحدتان را اینجا ثبت کنید. فقط درخواست‌های واحد خودتان را می‌بینید.
        </p>
      </header>

      <form onSubmit={handleSubmit} className="flex flex-col gap-4 border p-5">
        {templates.length > 0 && (
          <div className="flex flex-col gap-2">
            <Label>درخواست‌های رایج</Label>
            <div className="flex flex-wrap gap-2">
              {templates.map((template) => (
                <button
                  key={template.id}
                  type="button"
                  onClick={() => applyTemplate(template)}
                  className="flex items-center gap-2 border px-3 py-2 text-sm transition-colors hover:border-accent hover:bg-secondary/40"
                >
                  <TemplateIcon name={template.icon} />
                  {template.title}
                </button>
              ))}
            </div>
            <p className="text-xs text-muted-foreground">
              با انتخاب هرکدام، فیلدهای زیر پر می‌شوند و هنوز قابل ویرایش‌اند.
            </p>
          </div>
        )}

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="it-request-title">موضوع *</Label>
          <Input
            id="it-request-title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="مثلاً: پرینتر پذیرش کاغذ گیر می‌کند"
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="it-request-description">توضیح</Label>
          <Textarea
            id="it-request-description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={3}
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="it-request-photo">عکس مشکل (اختیاری)</Label>
          <label
            htmlFor="it-request-photo"
            className="flex cursor-pointer items-center gap-2 border border-dashed px-3 py-2 text-sm text-muted-foreground transition-colors hover:bg-secondary/40"
          >
            <ImagePlus className="size-4 shrink-0" />
            {photo ? photo.name : "انتخاب تصویر…"}
          </label>
          <input
            id="it-request-photo"
            type="file"
            accept="image/*"
            className="sr-only"
            onChange={(e) => setPhoto(e.target.files?.[0] ?? null)}
          />
        </div>

        <div className="flex flex-wrap items-end justify-between gap-4">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="it-request-priority">فوریت</Label>
            <Select value={priority} onValueChange={(value) => setPriority(value as ITPriority)}>
              <SelectTrigger id="it-request-priority" className="w-40">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {PRIORITIES.map((value) => (
                  <SelectItem key={value} value={value}>
                    {itPriorityLabels[value]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <Button type="submit" className="gap-1.5" disabled={isSubmitting || !title.trim()}>
            {isSubmitting ? <Loader2 className="animate-spin" /> : <Send />}
            ارسال به IT
          </Button>
        </div>
      </form>

      <section className="flex flex-col gap-3">
        <h2 className="display-3">درخواست‌های واحد شما</h2>
        {loadError && <FormError message={loadError} />}
        <div className="flex flex-col border">
          {requests === null && !loadError ? (
            [0, 1].map((i) => (
              <div key={i} className="flex flex-col gap-2 border-t px-4 py-3 first:border-t-0">
                <Skeleton className="h-4 w-48" />
                <Skeleton className="h-3 w-32" />
              </div>
            ))
          ) : requests && requests.length === 0 ? (
            <p className="px-4 py-6 text-center text-sm text-muted-foreground">
              هنوز درخواستی به IT نفرستاده‌اید.
            </p>
          ) : (
            requests?.map((request) => (
              <div key={request.id} className="flex flex-col gap-3 border-t px-4 py-3 text-sm first:border-t-0">
                <div className="flex items-center justify-between gap-4">
                  <div className="flex min-w-0 flex-col gap-1">
                    <span>{request.title}</span>
                    <span className="text-xs text-muted-foreground">
                      {request.requested_by_username && `${request.requested_by_username} · `}
                      <RelativeTime iso={request.created_at} />
                      {request.assigned_to_username && ` · پیگیری: ${request.assigned_to_username}`}
                    </span>
                  </div>
                  <div className="flex shrink-0 items-center gap-1.5">
                    <Badge variant={PRIORITY_VARIANT[request.priority]} className="font-normal">
                      {itPriorityLabels[request.priority]}
                    </Badge>
                    <Badge variant={STATUS_VARIANT[request.status]} className="font-normal">
                      {itRequestStatusLabels[request.status]}
                    </Badge>
                  </div>
                </div>

                {request.attachments.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {request.attachments.map((attachment) => (
                      <a
                        key={attachment.id}
                        href={attachment.image}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="border p-0.5 transition-colors hover:border-accent"
                      >
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img
                          src={attachment.image}
                          alt="عکس پیوست درخواست"
                          className="size-16 object-cover"
                        />
                      </a>
                    ))}
                  </div>
                )}

                {request.rating !== null ? (
                  <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                    <span>بازخورد شما:</span>
                    <StarDisplay value={request.rating} className="size-4" />
                    {request.feedback && <span>«{request.feedback}»</span>}
                  </div>
                ) : request.can_be_rated ? (
                  ratingFor === request.id ? (
                    <div className="flex flex-col gap-2 border-t pt-3">
                      <Label>کار IT را چطور دیدید؟</Label>
                      <StarPicker value={rating} onChange={setRating} disabled={isRating} />
                      <Textarea
                        value={feedback}
                        onChange={(e) => setFeedback(e.target.value)}
                        rows={2}
                        placeholder="توضیح اختیاری…"
                      />
                      <div className="flex gap-2">
                        <Button
                          type="button"
                          size="sm"
                          disabled={rating < 1 || isRating}
                          onClick={() => submitRating(request.id)}
                          className="gap-1.5"
                        >
                          {isRating ? <Loader2 className="animate-spin" /> : <Sparkles />}
                          ثبت بازخورد
                        </Button>
                        <Button
                          type="button"
                          size="sm"
                          variant="ghost"
                          disabled={isRating}
                          onClick={() => setRatingFor(null)}
                        >
                          بی‌خیال
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      className="self-start"
                      onClick={() => openRating(request)}
                    >
                      ثبت بازخورد
                    </Button>
                  )
                ) : null}
              </div>
            ))
          )}
        </div>
      </section>
    </main>
  );
}
