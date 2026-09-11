"use client";

import { useEffect, useState, type ReactNode } from "react";
import { AlertTriangle, Clock } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { FormError } from "@/components/form-error";
import { RelativeTime } from "@/components/relative-time";
import {
  ApiError,
  getAccessToken,
  getAdminStatsSummary,
  getDepartmentStatsSummary,
} from "@/lib/api/client";
import { decodeAccessToken } from "@/lib/api/tokens";
import type {
  AdminStatsSummary,
  DepartmentOperatorLoad,
  DepartmentStatsSummary,
  TicketStatus,
} from "@/lib/api/types";
import { formatDurationMinutes, formatNumber } from "@/lib/format";
import { statusLabels } from "@/lib/ticket-labels";

const STATUS_ORDER: TicketStatus[] = ["OPEN", "IN_PROGRESS", "RESOLVED", "CANCELLED"];

type Summary =
  | { scope: "hotel"; data: AdminStatsSummary }
  | { scope: "department"; data: DepartmentStatsSummary };

/**
 * The Django Admin "Stats Summary", brought into the operator panel.
 *
 * Which numbers you get is decided by the server, not by this page:
 * admins call the hotel-wide endpoint (IsAdminOnly), everyone else the
 * department endpoint, which always scopes to the caller's own
 * department. The role check here only picks which endpoint to ask —
 * asking the wrong one just comes back 403.
 */
export default function StatsSummaryPage() {
  const role = decodeAccessToken(getAccessToken() ?? "")?.role ?? null;
  const [summary, setSummary] = useState<Summary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (role === null) return;
    let cancelled = false;

    const request: Promise<Summary> =
      role === "ADMIN"
        ? getAdminStatsSummary().then((data): Summary => ({ scope: "hotel", data }))
        : getDepartmentStatsSummary().then((data): Summary => ({ scope: "department", data }));

    request
      .then((result) => {
        if (!cancelled) setSummary(result);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : "خطا در دریافت خلاصهٔ آمار.");
        }
      });

    return () => {
      cancelled = true;
    };
  }, [role]);

  return (
    <main className="mx-auto flex w-full max-w-4xl flex-1 flex-col gap-8">
      <header className="flex flex-col gap-1">
        <p className="label-eyebrow">خلاصهٔ آمار</p>
        {summary ? (
          <h1 className="display-2 rule-accent">
            {summary.scope === "hotel" ? "کل هتل" : `واحد ${summary.data.department_name}`}
          </h1>
        ) : (
          <Skeleton className="h-9 w-44" />
        )}
        {summary && (
          <p className="pt-2 text-sm text-muted-foreground">
            آخرین محاسبه: <RelativeTime iso={summary.data.generated_at} />
          </p>
        )}
      </header>

      {error && <FormError message={error} />}

      {!summary && !error && (
        <div className="grid grid-cols-2 gap-px border bg-border sm:grid-cols-4">
          {STATUS_ORDER.map((status) => (
            <div key={status} className="flex flex-col gap-3 bg-card p-5">
              <Skeleton className="h-8 w-12" />
              <Skeleton className="h-3 w-20" />
            </div>
          ))}
        </div>
      )}

      {summary && (
        <>
          <section className="flex flex-col gap-px border bg-border">
            <div className="grid grid-cols-2 gap-px sm:grid-cols-4">
              {STATUS_ORDER.map((status) => (
                <StatTile
                  key={status}
                  label={statusLabels[status]}
                  value={formatNumber(summary.data.by_status[status])}
                />
              ))}
            </div>
            <div className="grid grid-cols-1 gap-px sm:grid-cols-2">
              <StatTile
                label="در حال حاضر معوق"
                value={formatNumber(summary.data.overdue_count)}
                tone={summary.data.overdue_count > 0 ? "alert" : "normal"}
                icon={<AlertTriangle className="size-3.5" />}
              />
              <StatTile
                label={`میانگین زمان رسیدگی — ${formatNumber(summary.data.resolution_window_days)} روز اخیر`}
                value={
                  summary.data.avg_resolution_minutes === null
                    ? "—"
                    : formatDurationMinutes(summary.data.avg_resolution_minutes)
                }
                icon={<Clock className="size-3.5" />}
              />
            </div>
          </section>

          {summary.scope === "hotel" ? (
            <DepartmentTable rows={summary.data.by_department} />
          ) : (
            <OperatorTable
              rows={summary.data.by_operator}
              windowDays={summary.data.resolution_window_days}
            />
          )}
        </>
      )}
    </main>
  );
}

function StatTile({
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

const th = "px-4 py-2.5 text-start font-medium";
const td = "px-4 py-2.5 tabular-nums";

function DepartmentTable({ rows }: { rows: AdminStatsSummary["by_department"] }) {
  return (
    <section className="flex flex-col gap-3">
      <h2 className="display-3">به تفکیک واحد</h2>
      <div className="overflow-x-auto border">
        <table className="w-full min-w-[34rem] text-sm">
          <thead className="bg-secondary/60 text-muted-foreground">
            <tr>
              <th className={th}>واحد</th>
              {STATUS_ORDER.map((status) => (
                <th key={status} className={th}>
                  {statusLabels[status]}
                </th>
              ))}
              <th className={th}>مجموع</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-6 text-center text-muted-foreground">
                  هنوز واحدی تعریف نشده است.
                </td>
              </tr>
            ) : (
              rows.map((row) => (
                <tr key={row.department_id} className="border-t">
                  <td className="px-4 py-2.5">{row.department_name}</td>
                  {[row.open, row.in_progress, row.resolved, row.cancelled].map((count, i) => (
                    <td key={STATUS_ORDER[i]} className={td}>
                      {formatNumber(count)}
                    </td>
                  ))}
                  <td className={`${td} font-medium`}>{formatNumber(row.total)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function OperatorTable({
  rows,
  windowDays,
}: {
  rows: DepartmentOperatorLoad[];
  windowDays: number;
}) {
  return (
    <section className="flex flex-col gap-3">
      <div className="flex flex-col gap-1">
        <h2 className="display-3">بار کاری اپراتورها</h2>
        <p className="text-sm text-muted-foreground">
          «فعال» یعنی درخواست‌های باز یا در حال بررسی که به آن اپراتور اختصاص دارد.
        </p>
      </div>
      <div className="overflow-x-auto border">
        <table className="w-full min-w-[26rem] text-sm">
          <thead className="bg-secondary/60 text-muted-foreground">
            <tr>
              <th className={th}>اپراتور</th>
              <th className={th}>فعال</th>
              <th className={th}>حل‌شده — {formatNumber(windowDays)} روز اخیر</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={3} className="px-4 py-6 text-center text-muted-foreground">
                  هیچ اپراتوری در این واحد تعریف نشده است.
                </td>
              </tr>
            ) : (
              rows.map((row) => (
                <tr key={row.operator_id} className="border-t">
                  <td className="px-4 py-2.5">
                    <span className="flex items-center gap-2">
                      {row.username}
                      {row.is_supervisor && (
                        <Badge variant="secondary" className="text-[11px] font-normal">
                          سرپرست
                        </Badge>
                      )}
                    </span>
                  </td>
                  <td className={td}>{formatNumber(row.active)}</td>
                  <td className={td}>{formatNumber(row.resolved_recent)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
