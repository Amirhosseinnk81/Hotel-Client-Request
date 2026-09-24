"use client";

import { useEffect, useState, type ReactNode } from "react";
import { AlertTriangle, Clock, Star, Target, Timer } from "lucide-react";

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
  RecentFeedback,
  TicketStatus,
} from "@/lib/api/types";
import { formatDurationMinutes, formatNumber } from "@/lib/format";
import { statusLabels } from "@/lib/ticket-labels";

const STATUS_ORDER: TicketStatus[] = ["OPEN", "IN_PROGRESS", "RESOLVED", "CANCELLED"];

/** SLA share, e.g. 87.5 -> "۸۷٫۵٪"; "—" when nothing was due in the window. */
const formatPercent = (value: number | null) => (value === null ? "—" : `${formatNumber(value)}٪`);

/** Average guest rating, e.g. 4.25 -> "۴٫۲۵ از ۵"; "—" when nobody rated. */
const formatRating = (value: number | null) => (value === null ? "—" : `${formatNumber(value)} از ۵`);

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
            {/* Two-stage SLA: first response (someone starts on it) and resolution. */}
            <div className="grid grid-cols-2 gap-px sm:grid-cols-4">
              <StatTile
                label="منتظر اولین پاسخ"
                value={formatNumber(summary.data.response_overdue_count)}
                tone={summary.data.response_overdue_count > 0 ? "alert" : "normal"}
                icon={<Timer className="size-3.5" />}
              />
              <StatTile
                label="میانگین زمان اولین پاسخ"
                value={
                  summary.data.avg_first_response_minutes === null
                    ? "—"
                    : formatDurationMinutes(summary.data.avg_first_response_minutes)
                }
                icon={<Clock className="size-3.5" />}
              />
              <StatTile
                label="اولین پاسخ به‌موقع"
                value={formatPercent(summary.data.response_sla_met_percent)}
                icon={<Target className="size-3.5" />}
              />
              <StatTile
                label="حل به‌موقع"
                value={formatPercent(summary.data.resolution_sla_met_percent)}
                icon={<Target className="size-3.5" />}
              />
            </div>
          </section>

          <RatingsSection
            average={summary.data.rating_avg}
            count={summary.data.rating_count}
            distribution={summary.data.rating_distribution}
            feedback={summary.data.recent_feedback}
            windowDays={summary.data.resolution_window_days}
            showDepartment={summary.scope === "hotel"}
          />

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
              <th className={th}>رضایت</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-4 py-6 text-center text-muted-foreground">
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
                  <td className={td}>
                    <RatingCell average={row.rating_avg} count={row.rating_count} />
                  </td>
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
              <th className={th}>رضایت</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-4 py-6 text-center text-muted-foreground">
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
                  <td className={td}>
                    <RatingCell average={row.rating_avg} count={row.rating_count} />
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function RatingCell({ average, count }: { average: number | null; count: number }) {
  if (average === null) return <span className="text-muted-foreground">—</span>;
  return (
    <span className="flex items-center gap-1">
      <Star className="size-3.5 fill-warning text-warning" aria-hidden />
      {formatNumber(average)}
      <span className="text-xs text-muted-foreground">({formatNumber(count)})</span>
    </span>
  );
}

/**
 * Guest satisfaction (inspired by Odoo Helpdesk's customer-ratings report):
 * the average, how the ratings spread over 1-5 stars, and the latest
 * written comments.
 */
function RatingsSection({
  average,
  count,
  distribution,
  feedback,
  windowDays,
  showDepartment,
}: {
  average: number | null;
  count: number;
  distribution: Record<"1" | "2" | "3" | "4" | "5", number>;
  feedback: RecentFeedback[];
  windowDays: number;
  showDepartment: boolean;
}) {
  const stars = ["5", "4", "3", "2", "1"] as const;
  return (
    <section className="flex flex-col gap-3">
      <div className="flex flex-col gap-1">
        <h2 className="display-3">رضایت مهمان</h2>
        <p className="text-sm text-muted-foreground">
          امتیاز مهمان‌ها به درخواست‌های حل‌شده در {formatNumber(windowDays)} روز اخیر.
        </p>
      </div>
      <div className="grid grid-cols-1 gap-px border bg-border sm:grid-cols-[14rem_1fr]">
        <StatTile
          label={`میانگین از ${formatNumber(count)} امتیاز`}
          value={formatRating(average)}
          icon={<Star className="size-3.5" />}
        />
        <div className="flex flex-col justify-center gap-1.5 bg-card p-5">
          {stars.map((star) => {
            const n = distribution[star];
            const share = count ? (n / count) * 100 : 0;
            return (
              <div key={star} className="flex items-center gap-3 text-xs">
                <span className="w-10 shrink-0 tabular-nums">{formatNumber(Number(star))} ★</span>
                <span className="h-2 flex-1 bg-secondary" aria-hidden>
                  <span className="block h-full bg-primary" style={{ width: `${share}%` }} />
                </span>
                <span className="w-8 shrink-0 text-end tabular-nums text-muted-foreground">
                  {formatNumber(n)}
                </span>
              </div>
            );
          })}
        </div>
      </div>
      {feedback.length > 0 && (
        <ul className="flex flex-col border">
          {feedback.map((item) => (
            <li key={item.ticket_id} className="flex flex-col gap-1 border-t px-4 py-3 text-sm first:border-t-0">
              <span className="flex flex-wrap items-center gap-2">
                <span className="tabular-nums text-warning" aria-label={`${item.rating} از ۵`}>
                  {"★".repeat(item.rating)}
                  <span className="text-muted-foreground/40">{"★".repeat(5 - item.rating)}</span>
                </span>
                <span className="text-muted-foreground">
                  «{item.title}»
                  {showDepartment && ` · ${item.department_name}`}
                  {item.operator && ` · ${item.operator}`}
                  {" · "}
                  <RelativeTime iso={item.resolved_at} />
                </span>
              </span>
              <p>{item.feedback}</p>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
