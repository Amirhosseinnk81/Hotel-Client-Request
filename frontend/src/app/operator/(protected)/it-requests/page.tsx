"use client";

import { useCallback, useEffect, useState } from "react";
import { Loader2, Send } from "lucide-react";

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
import { PRIORITY_VARIANT } from "@/components/it-ops/today-panel";
import { toast } from "@/hooks/use-toast";
import { ApiError, createOutgoingItRequest, getOutgoingItRequests } from "@/lib/api/client";
import type { ITPriority, ITRequestStatus, OutgoingITRequest } from "@/lib/api/types";
import { itPriorityLabels, itRequestStatusLabels } from "@/lib/it-ops";

const STATUS_VARIANT: Record<ITRequestStatus, "secondary" | "warning" | "success" | "destructive"> = {
  PENDING: "secondary",
  IN_PROGRESS: "warning",
  COMPLETED: "success",
  REJECTED: "destructive",
};

const PRIORITIES: ITPriority[] = ["LOW", "MEDIUM", "HIGH", "CRITICAL"];

/**
 * «درخواست از IT» — how any department asks IT for something (a printer,
 * network access, a new PC) from its own panel, and follows it. Backed by
 * /it-ops/outgoing-requests/: the server fixes the department and
 * requester from the logged-in operator and only ever shows this
 * department's own requests. Status and assignee are IT's to change.
 */
export default function ITRequestsPage() {
  const [requests, setRequests] = useState<OutgoingITRequest[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState<ITPriority>("MEDIUM");
  const [isSubmitting, setIsSubmitting] = useState(false);

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
      toast({
        title: "درخواست به IT رفت",
        description: `«${created.title}» ثبت شد؛ وضعیتش را همین‌جا دنبال کنید.`,
        variant: "success",
      });
      setTitle("");
      setDescription("");
      setPriority("MEDIUM");
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
              <div
                key={request.id}
                className="flex items-center justify-between gap-4 border-t px-4 py-3 text-sm first:border-t-0"
              >
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
            ))
          )}
        </div>
      </section>
    </main>
  );
}
