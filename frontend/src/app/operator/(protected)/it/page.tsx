"use client";

import { useCallback, useEffect, useState, type ReactNode } from "react";
import { AlertTriangle, BedDouble, CheckCheck, ListTodo } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { FormError } from "@/components/form-error";
import { RelativeTime } from "@/components/relative-time";
import { toast } from "@/hooks/use-toast";
import { ApiError, getItOpsToday, markItProcessDone } from "@/lib/api/client";
import type { ITPriority, ITTodayDashboard } from "@/lib/api/types";
import { formatNumber } from "@/lib/format";
import {
  canMarkProcessDone,
  getITViewer,
  itFrequencyLabels,
  itPriorityLabels,
  itProcessTypeLabels,
  itRequestStatusLabels,
  itTaskStatusLabels,
} from "@/lib/it-ops";

const PRIORITY_VARIANT: Record<ITPriority, "destructive" | "warning" | "secondary" | "outline"> = {
  CRITICAL: "destructive",
  HIGH: "warning",
  MEDIUM: "secondary",
  LOW: "outline",
};

/**
 * IT Ops — "today" (GET /it-ops/today/): what is due or overdue, which
 * requests from other departments are still open, and live room
 * occupancy. For IT staff and admins; the server answers 403 to anyone
 * else, and the nav link is only shown to them in the first place.
 */
export default function ITOpsTodayPage() {
  const [viewer] = useState(getITViewer);
  const [data, setData] = useState<ITTodayDashboard | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [markingId, setMarkingId] = useState<number | null>(null);

  const load = useCallback(() => {
    return getItOpsToday()
      .then((result) => {
        setData(result);
        setError(null);
      })
      .catch((err) => {
        setError(err instanceof ApiError ? err.message : "خطا در دریافت داشبورد IT.");
      });
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleMarkDone = async (processId: number, title: string) => {
    setMarkingId(processId);
    try {
      await markItProcessDone(processId);
      toast({ title: "ثبت شد", description: `«${title}» انجام‌شده ثبت شد.` });
      await load();
    } catch (err) {
      toast({
        title: "ثبت نشد",
        description: err instanceof ApiError ? err.message : "خطا در ثبت انجام فرایند.",
        variant: "destructive",
      });
    } finally {
      setMarkingId(null);
    }
  };

  return (
    <main className="mx-auto flex w-full max-w-5xl flex-1 flex-col gap-8">
      <header className="flex flex-col gap-1">
        <p className="label-eyebrow">عملیات IT</p>
        <h1 className="display-2 rule-accent">کارهای امروز</h1>
        {data && (
          <p className="pt-2 text-sm text-muted-foreground">
            آخرین محاسبه: <RelativeTime iso={data.generated_at} />
          </p>
        )}
      </header>

      {error && <FormError message={error} />}

      {!data && !error && (
        <div className="grid grid-cols-2 gap-px border bg-border sm:grid-cols-4">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="flex flex-col gap-3 bg-card p-5">
              <Skeleton className="h-8 w-12" />
              <Skeleton className="h-3 w-24" />
            </div>
          ))}
        </div>
      )}

      {data && (
        <>
          <section className="grid grid-cols-2 gap-px border bg-border sm:grid-cols-4">
            <Tile
              label="کارهای سررسیده"
              value={formatNumber(data.tasks_due_or_overdue.length)}
              icon={<ListTodo className="size-3.5" />}
            />
            <Tile
              label="فرایندهای سررسیده"
              value={formatNumber(data.processes_due_or_overdue.length)}
              tone={data.processes_due_or_overdue.some((p) => p.is_overdue) ? "alert" : "normal"}
              icon={<AlertTriangle className="size-3.5" />}
            />
            <Tile
              label="کارهای باز من"
              value={formatNumber(data.my_open_tasks_count)}
              icon={<CheckCheck className="size-3.5" />}
            />
            <Tile
              label={`اشغال اتاق — ${formatNumber(data.room_stats_today.occupied_rooms)} از ${formatNumber(data.room_stats_today.total_rooms)}`}
              value={`${formatNumber(data.room_stats_today.occupancy_rate)}٪`}
              icon={<BedDouble className="size-3.5" />}
            />
          </section>

          <Section title="فرایندهای سررسیده" empty="امروز فرایندی سررسید نشده است.">
            {data.processes_due_or_overdue.map((process) => (
              <Row key={process.id}>
                <div className="flex min-w-0 flex-col gap-1">
                  <span className="flex flex-wrap items-center gap-2">
                    {process.title}
                    {process.is_overdue && (
                      <Badge variant="destructive" className="text-[11px] font-normal">
                        معوق
                      </Badge>
                    )}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {itProcessTypeLabels[process.process_type]} · {itFrequencyLabels[process.frequency]}
                    {process.responsible_username && ` · مسئول: ${process.responsible_username}`}
                    {process.next_due_at && (
                      <>
                        {" · سررسید "}
                        <RelativeTime iso={process.next_due_at} />
                      </>
                    )}
                  </span>
                </div>
                {canMarkProcessDone(viewer, process) && (
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={markingId === process.id}
                    onClick={() => handleMarkDone(process.id, process.title)}
                  >
                    انجام شد
                  </Button>
                )}
              </Row>
            ))}
          </Section>

          <Section title="کارهای سررسیده" empty="کار سررسیده‌ای نیست.">
            {data.tasks_due_or_overdue.map((task) => (
              <Row key={task.id}>
                <div className="flex min-w-0 flex-col gap-1">
                  <span>{task.title}</span>
                  <span className="text-xs text-muted-foreground">
                    {itTaskStatusLabels[task.status]}
                    {task.assigned_to_username && ` · ${task.assigned_to_username}`}
                    {task.due_date && (
                      <>
                        {" · سررسید "}
                        <RelativeTime iso={task.due_date} />
                      </>
                    )}
                  </span>
                </div>
                <Badge variant={PRIORITY_VARIANT[task.priority]} className="font-normal">
                  {itPriorityLabels[task.priority]}
                </Badge>
              </Row>
            ))}
          </Section>

          <Section title="درخواست‌های باز واحدها" empty="درخواست بازی از واحدها نیست.">
            {data.open_department_requests.map((request) => (
              <Row key={request.id}>
                <div className="flex min-w-0 flex-col gap-1">
                  <span>{request.title}</span>
                  <span className="text-xs text-muted-foreground">
                    {request.requesting_department_name ?? "واحد نامشخص"}
                    {" · "}
                    {itRequestStatusLabels[request.status]}
                    {request.assigned_to_username && ` · ${request.assigned_to_username}`}
                    {" · "}
                    <RelativeTime iso={request.created_at} />
                  </span>
                </div>
                <Badge variant={PRIORITY_VARIANT[request.priority]} className="font-normal">
                  {itPriorityLabels[request.priority]}
                </Badge>
              </Row>
            ))}
          </Section>
        </>
      )}
    </main>
  );
}

function Tile({
  label,
  value,
  tone = "normal",
  icon,
}: {
  label: string;
  value: string;
  tone?: "normal" | "alert";
  icon?: ReactNode;
}) {
  return (
    <div className="flex flex-col gap-2 bg-card p-5">
      <span
        className={`text-3xl font-light tabular-nums tracking-tight ${
          tone === "alert" ? "text-destructive" : "text-foreground"
        }`}
      >
        {value}
      </span>
      <span className="label-eyebrow flex items-center gap-1.5">
        {icon}
        {label}
      </span>
    </div>
  );
}

function Section({
  title,
  empty,
  children,
}: {
  title: string;
  empty: string;
  children: ReactNode[];
}) {
  return (
    <section className="flex flex-col gap-3">
      <h2 className="display-3">{title}</h2>
      <div className="flex flex-col border">
        {children.length === 0 ? (
          <p className="px-4 py-6 text-center text-sm text-muted-foreground">{empty}</p>
        ) : (
          children
        )}
      </div>
    </section>
  );
}

function Row({ children }: { children: ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-4 border-t px-4 py-3 text-sm first:border-t-0">
      {children}
    </div>
  );
}
