"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { RelativeTime } from "@/components/relative-time";
import { ITResourcePanel, type ITResourceConfig } from "@/components/it-ops/resource-panel";
import { ITTodayPanel, PRIORITY_VARIANT } from "@/components/it-ops/today-panel";
import { toast } from "@/hooks/use-toast";
import {
  ApiError,
  getDepartments,
  getItStaff,
  listItItems,
  markItProcessDone,
} from "@/lib/api/client";
import type {
  Department,
  ITGoalStatus,
  ITGoalType,
  ITPriority,
  ITProcessFrequency,
  ITProcessType,
  ITProject,
  ITProjectStatus,
  ITStaffMember,
  ITTaskStatus,
} from "@/lib/api/types";
import { formatDateOnly } from "@/lib/format";
import {
  canMarkProcessDone,
  getITViewer,
  isItFieldEditable,
  itFrequencyLabels,
  itGoalStatusLabels,
  itGoalTypeLabels,
  itPriorityLabels,
  itProcessStatusLabels,
  itProcessTypeLabels,
  itProjectStatusLabels,
  itRequestStatusLabels,
  itRequestStatusOptions,
  itTaskStatusLabels,
  type ITViewer,
} from "@/lib/it-ops";
import type { ITFieldSpec } from "@/components/it-ops/item-dialog";

const TABS = [
  { key: "today", label: "امروز" },
  { key: "tasks", label: "کارها" },
  { key: "department-requests", label: "درخواست واحدها" },
  { key: "processes", label: "فرایندها" },
  { key: "projects", label: "پروژه‌ها" },
  { key: "goals", label: "اهداف" },
] as const;
type TabKey = (typeof TABS)[number]["key"];

const options = <T extends string>(labels: Record<T, string>, keys?: T[]) =>
  (keys ?? (Object.keys(labels) as T[])).map((value) => ({ value, label: labels[value] }));

/** Lookups the forms need for their dropdowns, loaded once for the page. */
interface Lookups {
  staff: ITStaffMember[];
  departments: Department[];
  projects: ITProject[];
}

/**
 * IT Ops (/operator/it): the "today" dashboard plus a tab per resource with
 * create / edit / delete. For IT staff and admins — the server answers 403
 * to anyone else, and the nav link is only shown to them anyway.
 *
 * The active tab lives in ?tab= so a reload or a shared link keeps it.
 * useSearchParams() needs a Suspense boundary (same as guest/login).
 */
export default function ITOpsPage() {
  return (
    <Suspense fallback={<Skeleton className="mx-auto h-9 w-full max-w-5xl" />}>
      <ITOpsPageContent />
    </Suspense>
  );
}

function ITOpsPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const requested = searchParams.get("tab");
  const tab: TabKey = TABS.some((t) => t.key === requested) ? (requested as TabKey) : "today";

  const [viewer] = useState(getITViewer);
  const [lookups, setLookups] = useState<Lookups>({ staff: [], departments: [], projects: [] });

  useEffect(() => {
    let cancelled = false;
    Promise.all([getItStaff(), getDepartments(), listItItems("projects")])
      .then(([staff, departments, projects]) => {
        if (!cancelled) setLookups({ staff, departments, projects });
      })
      .catch(() => {
        // Dropdowns just stay empty; the lists themselves report their own errors.
      });
    return () => {
      cancelled = true;
    };
  }, [tab]);

  return (
    <main className="mx-auto flex w-full max-w-5xl flex-1 flex-col gap-8">
      <header className="flex flex-col gap-1">
        <p className="label-eyebrow">عملیات IT</p>
        <h1 className="display-2 rule-accent">{TABS.find((t) => t.key === tab)?.label}</h1>
      </header>

      <nav className="flex flex-wrap gap-1 border-b text-sm" aria-label="بخش‌های IT">
        {TABS.map((t) => (
          <button
            key={t.key}
            type="button"
            onClick={() => router.replace(`/operator/it?tab=${t.key}`)}
            className={`-mb-px px-3 py-2 transition-colors ${
              t.key === tab
                ? "border-b-2 border-accent text-foreground"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            {t.label}
          </button>
        ))}
      </nav>

      {tab === "today" && <ITTodayPanel viewer={viewer} />}
      {tab === "tasks" && <ITResourcePanel config={taskConfig(viewer, lookups)} viewer={viewer} />}
      {tab === "department-requests" && (
        <ITResourcePanel config={requestConfig(viewer, lookups)} viewer={viewer} />
      )}
      {tab === "processes" && <ITResourcePanel config={processConfig(viewer, lookups)} viewer={viewer} />}
      {tab === "projects" && <ITResourcePanel config={projectConfig(lookups)} viewer={viewer} />}
      {tab === "goals" && <ITResourcePanel config={goalConfig(lookups)} viewer={viewer} />}
    </main>
  );
}

// ---------------------------------------------------------------------------
// Per-resource config: which fields, and how a row reads.
// ---------------------------------------------------------------------------

const staffOptions = (lookups: Lookups) =>
  lookups.staff.map((member) => ({
    value: String(member.id),
    label: member.is_supervisor ? `${member.username} (سرپرست)` : member.username,
  }));

/** Drop what this viewer may not send in this mode (see isItFieldEditable). */
const visible = (
  viewer: ITViewer,
  resource: Parameters<typeof isItFieldEditable>[1],
  mode: "create" | "edit",
  specs: ITFieldSpec[]
) => specs.filter((spec) => isItFieldEditable(viewer, resource, spec.name, mode));

function PriorityBadge({ priority }: { priority: ITPriority }) {
  return (
    <Badge variant={PRIORITY_VARIANT[priority]} className="font-normal">
      {itPriorityLabels[priority]}
    </Badge>
  );
}

function taskConfig(viewer: ITViewer, lookups: Lookups): ITResourceConfig<"tasks"> {
  return {
    resource: "tasks",
    noun: "کار",
    emptyText: "کاری ثبت نشده است.",
    fields: (mode) =>
      visible(viewer, "tasks", mode, [
        { name: "title", label: "عنوان", kind: "text", required: true },
        { name: "description", label: "توضیح", kind: "textarea" },
        { name: "status", label: "وضعیت", kind: "select", options: options<ITTaskStatus>(itTaskStatusLabels) },
        { name: "priority", label: "اولویت", kind: "select", options: options<ITPriority>(itPriorityLabels) },
        {
          name: "assigned_to",
          label: "مسئول",
          kind: "select",
          nullable: true,
          numeric: true,
          options: staffOptions(lookups),
        },
        { name: "due_date", label: "سررسید", kind: "datetime" },
      ]),
    renderRow: (task) => ({
      primary: task.title,
      secondary: (
        <>
          {itTaskStatusLabels[task.status]}
          {task.assigned_to_username && ` · ${task.assigned_to_username}`}
          {task.due_date && (
            <>
              {" · سررسید "}
              <RelativeTime iso={task.due_date} />
            </>
          )}
        </>
      ),
      aside: <PriorityBadge priority={task.priority} />,
    }),
  };
}

function requestConfig(viewer: ITViewer, lookups: Lookups): ITResourceConfig<"department-requests"> {
  return {
    resource: "department-requests",
    noun: "درخواست",
    emptyText: "درخواستی از واحدها ثبت نشده است.",
    fields: (mode) =>
      visible(viewer, "department-requests", mode, [
        { name: "title", label: "عنوان", kind: "text", required: true },
        { name: "description", label: "توضیح", kind: "textarea" },
        ...(mode === "create"
          ? ([
              {
                name: "requesting_department",
                label: "واحد درخواست‌دهنده",
                kind: "select",
                numeric: true,
                required: true,
                options: lookups.departments.map((d) => ({ value: String(d.id), label: d.name })),
              },
              { name: "requested_by_name", label: "نام درخواست‌دهنده", kind: "text" },
            ] satisfies ITFieldSpec[])
          : []),
        {
          name: "status",
          label: "وضعیت",
          kind: "select",
          options: options(itRequestStatusLabels, itRequestStatusOptions(viewer)),
        },
        { name: "priority", label: "اولویت", kind: "select", options: options<ITPriority>(itPriorityLabels) },
        {
          name: "assigned_to",
          label: "مسئول",
          kind: "select",
          nullable: true,
          numeric: true,
          options: staffOptions(lookups),
        },
      ]),
    renderRow: (request) => ({
      primary: request.title,
      secondary: (
        <>
          {request.requesting_department_name ?? "واحد نامشخص"}
          {(request.requested_by_username || request.requested_by_name) &&
            ` (${request.requested_by_username ?? request.requested_by_name})`}
          {" · "}
          {itRequestStatusLabels[request.status]}
          {request.assigned_to_username && ` · ${request.assigned_to_username}`}
          {" · "}
          <RelativeTime iso={request.created_at} />
        </>
      ),
      aside: <PriorityBadge priority={request.priority} />,
    }),
  };
}

function processConfig(viewer: ITViewer, lookups: Lookups): ITResourceConfig<"processes"> {
  return {
    resource: "processes",
    noun: "فرایند",
    emptyText: "فرایندی تعریف نشده است.",
    fields: () => [
      { name: "title", label: "عنوان", kind: "text", required: true },
      { name: "description", label: "توضیح", kind: "textarea" },
      {
        name: "process_type",
        label: "نوع",
        kind: "select",
        required: true,
        options: options<ITProcessType>(itProcessTypeLabels),
      },
      {
        name: "frequency",
        label: "تکرار",
        kind: "select",
        options: options<ITProcessFrequency>(itFrequencyLabels),
      },
      { name: "status", label: "وضعیت", kind: "select", options: options(itProcessStatusLabels) },
      {
        name: "responsible",
        label: "مسئول",
        kind: "select",
        nullable: true,
        numeric: true,
        options: staffOptions(lookups),
      },
      {
        name: "department",
        label: "واحد مرتبط",
        kind: "select",
        nullable: true,
        numeric: true,
        options: lookups.departments.map((d) => ({ value: String(d.id), label: d.name })),
      },
      // Filled in automatically for recurring processes; set by hand only to postpone a run.
      { name: "next_due_at", label: "سررسید بعدی (برای جابه‌جایی دستی)", kind: "datetime" },
    ],
    renderRow: (process) => ({
      primary: (
        <span className="flex flex-wrap items-center gap-2">
          {process.title}
          {process.is_overdue && (
            <Badge variant="destructive" className="text-[11px] font-normal">
              معوق
            </Badge>
          )}
        </span>
      ),
      secondary: (
        <>
          {itProcessTypeLabels[process.process_type]} · {itFrequencyLabels[process.frequency]} ·{" "}
          {itProcessStatusLabels[process.status]}
          {process.responsible_username && ` · مسئول: ${process.responsible_username}`}
          {process.next_due_at && (
            <>
              {" · سررسید "}
              <RelativeTime iso={process.next_due_at} />
            </>
          )}
        </>
      ),
    }),
    rowActions: (process, reload) =>
      canMarkProcessDone(viewer, process) && (
        <Button
          size="sm"
          variant="outline"
          onClick={async () => {
            try {
              await markItProcessDone(process.id);
              toast({ title: "ثبت شد", description: `«${process.title}» انجام‌شده ثبت شد.` });
              reload();
            } catch (err) {
              toast({
                title: "ثبت نشد",
                description: err instanceof ApiError ? err.message : "لطفاً دوباره تلاش کنید.",
                variant: "destructive",
              });
            }
          }}
        >
          انجام شد
        </Button>
      ),
  };
}

function projectConfig(lookups: Lookups): ITResourceConfig<"projects"> {
  return {
    resource: "projects",
    noun: "پروژه",
    emptyText: "پروژه‌ای ثبت نشده است.",
    fields: () => [
      { name: "title", label: "عنوان", kind: "text", required: true },
      { name: "description", label: "توضیح", kind: "textarea" },
      { name: "status", label: "وضعیت", kind: "select", options: options<ITProjectStatus>(itProjectStatusLabels) },
      { name: "priority", label: "اولویت", kind: "select", options: options<ITPriority>(itPriorityLabels) },
      {
        name: "owner",
        label: "مالک",
        kind: "select",
        nullable: true,
        numeric: true,
        options: staffOptions(lookups),
      },
      { name: "start_date", label: "شروع", kind: "date" },
      { name: "due_date", label: "پایان", kind: "date" },
    ],
    renderRow: (project) => ({
      primary: project.title,
      secondary: (
        <>
          {itProjectStatusLabels[project.status]}
          {project.owner_username && ` · ${project.owner_username}`}
          {project.due_date && ` · تا ${formatDateOnly(project.due_date)}`}
        </>
      ),
      aside: <PriorityBadge priority={project.priority} />,
    }),
  };
}

function goalConfig(lookups: Lookups): ITResourceConfig<"goals"> {
  return {
    resource: "goals",
    noun: "هدف",
    emptyText: "هدفی ثبت نشده است.",
    fields: () => [
      { name: "title", label: "عنوان", kind: "text", required: true },
      { name: "description", label: "توضیح", kind: "textarea" },
      {
        name: "goal_type",
        label: "بازه",
        kind: "select",
        required: true,
        options: options<ITGoalType>(itGoalTypeLabels),
      },
      { name: "status", label: "وضعیت", kind: "select", options: options<ITGoalStatus>(itGoalStatusLabels) },
      { name: "target_date", label: "تاریخ هدف", kind: "date" },
      {
        name: "owner",
        label: "مالک",
        kind: "select",
        nullable: true,
        numeric: true,
        options: staffOptions(lookups),
      },
      {
        name: "related_project",
        label: "پروژهٔ مرتبط",
        kind: "select",
        nullable: true,
        numeric: true,
        options: lookups.projects.map((p) => ({ value: String(p.id), label: p.title })),
      },
    ],
    renderRow: (goal) => ({
      primary: goal.title,
      secondary: (
        <>
          {itGoalTypeLabels[goal.goal_type]} · {itGoalStatusLabels[goal.status]}
          {goal.related_project_title && ` · ${goal.related_project_title}`}
          {goal.target_date && ` · تا ${formatDateOnly(goal.target_date)}`}
        </>
      ),
    }),
  };
}
