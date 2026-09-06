"use client";

import { useEffect, useState } from "react";
import type { ComponentType } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useForm, useWatch, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { ArrowRight, ImagePlus, Send, Sparkles } from "lucide-react";
import * as LucideIcons from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { FormError } from "@/components/form-error";
import { toast } from "@/hooks/use-toast";
import { priorityLabels } from "@/lib/ticket-labels";
import {
  ApiError,
  addGuestTicketAttachment,
  createTicket,
  getCategories,
  getDepartments,
  getQuickTemplates,
} from "@/lib/api/client";
import type {
  Category,
  Department,
  QuickRequestTemplate,
  TicketPriority,
} from "@/lib/api/types";

const priorityOptions: { value: TicketPriority; label: string }[] = (
  Object.keys(priorityLabels) as TicketPriority[]
).map((value) => ({ value, label: priorityLabels[value] }));

/** e.g. 15 -> "۱۵ دقیقه", 90 -> "۱ ساعت و ۳۰ دقیقه" (Stage 2.9). */
function formatEstimatedResponse(minutes: number): string {
  const fa = (n: number) => new Intl.NumberFormat("fa-IR").format(n);

  if (minutes < 60) {
    return `${fa(minutes)} دقیقه`;
  }

  const hours = Math.floor(minutes / 60);
  const remainder = minutes % 60;
  return remainder === 0
    ? `${fa(hours)} ساعت`
    : `${fa(hours)} ساعت و ${fa(remainder)} دقیقه`;
}

const newTicketSchema = z.object({
  title: z.string().min(3, "عنوان باید حداقل ۳ حرف باشد"),
  description: z.string().min(5, "توضیحات باید حداقل ۵ حرف باشد"),
  department: z.string().min(1, "واحد را انتخاب کنید"),
  category: z.string().min(1, "دسته‌بندی را انتخاب کنید"),
  priority: z.enum(["LOW", "NORMAL", "HIGH", "URGENT"]),
});

type NewTicketForm = z.infer<typeof newTicketSchema>;

/** Renders a QuickRequestTemplate.icon (a lucide-react name) with a safe fallback. */
function QuickTemplateIcon({ name }: { name: string }) {
  const Icon = (LucideIcons as unknown as Record<string, ComponentType<{ className?: string }>>)[
    name
  ];
  const Resolved = Icon ?? Sparkles;
  return <Resolved className="size-5" />;
}

export default function NewTicketPage() {
  const router = useRouter();
  const [departments, setDepartments] = useState<Department[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [quickTemplates, setQuickTemplates] = useState<QuickRequestTemplate[]>([]);
  const [isLoadingOptions, setIsLoadingOptions] = useState(true);
  const [optionsError, setOptionsError] = useState<string | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);
  const [attachmentFile, setAttachmentFile] = useState<File | null>(null);
  const [attachmentError, setAttachmentError] = useState<string | null>(null);
  const [submittedTicket, setSubmittedTicket] = useState<{
    id: number;
    title: string;
  } | null>(null);

  const {
    register,
    control,
    handleSubmit,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<NewTicketForm>({
    resolver: zodResolver(newTicketSchema),
    defaultValues: { title: "", description: "", department: "", category: "", priority: "NORMAL" },
  });

  const selectedCategoryId = useWatch({ control, name: "category" });
  const selectedCategory = categories.find(
    (cat) => String(cat.id) === selectedCategoryId
  );

  useEffect(() => {
    let cancelled = false;

    Promise.all([getDepartments(), getCategories()])
      .then(([deps, cats]) => {
        if (cancelled) return;
        setDepartments(deps);
        setCategories(cats);
      })
      .catch((err) => {
        if (cancelled) return;
        setOptionsError(
          err instanceof ApiError ? err.message : "خطا در دریافت لیست واحدها و دسته‌بندی‌ها."
        );
      })
      .finally(() => {
        if (!cancelled) setIsLoadingOptions(false);
      });

    // Non-essential — a failure here shouldn't block the form itself,
    // it just means the quick-request shortcuts row doesn't show.
    getQuickTemplates()
      .then((templates) => {
        if (!cancelled) setQuickTemplates(templates);
      })
      .catch(() => {
        /* silently degrade to no shortcuts */
      });

    return () => {
      cancelled = true;
    };
  }, []);

  // Holds the confirmation on screen just long enough to register, then
  // moves the guest on to their ticket list. Cleared on unmount so a
  // guest who navigates away mid-beat doesn't get yanked back.
  useEffect(() => {
    if (!submittedTicket) return;

    const timer = window.setTimeout(() => {
      router.push("/guest/tickets");
    }, 1600);

    return () => window.clearTimeout(timer);
  }, [submittedTicket, router]);

  const onSubmit = async (data: NewTicketForm) => {
    setApiError(null);
    setAttachmentError(null);
    try {
      const ticket = await createTicket({
        title: data.title,
        description: data.description,
        department: Number(data.department),
        category: Number(data.category),
        priority: data.priority,
      });

      if (attachmentFile) {
        try {
          await addGuestTicketAttachment(ticket.id, attachmentFile);
        } catch (attachmentErr) {
          // The ticket itself was created successfully — don't block the
          // guest on a photo failure, just let them know it didn't attach.
          toast({
            title: "درخواست ثبت شد، ولی عکس پیوست نشد",
            description:
              attachmentErr instanceof ApiError
                ? attachmentErr.message
                : "خطا در آپلود تصویر.",
            variant: "destructive",
          });
        }
      }

      // Deliberately NOT an immediate redirect. Usability testing on
      // hotel apps repeatedly turns up the same failure: an action
      // succeeds, the screen changes, and the guest is left unsure
      // whether it actually went through. A short, explicit "ثبت شد"
      // beat with the ticket number closes that loop before we navigate.
      setSubmittedTicket({ id: ticket.id, title: ticket.title });
    } catch (error) {
      setApiError(error instanceof ApiError ? error.message : "خطایی رخ داد. لطفاً دوباره تلاش کنید.");
    }
  };

  const applyQuickTemplate = (template: QuickRequestTemplate) => {
    setValue("title", template.title, { shouldValidate: true });
    setValue("department", String(template.department), { shouldValidate: true });
    setValue("category", String(template.category), { shouldValidate: true });
  };

  if (submittedTicket) {
    return (
      <main className="mx-auto flex w-full max-w-lg flex-1 flex-col justify-center px-2 py-20">
        <div className="confirm-rise flex flex-col items-center text-center">
          <svg
            className="confirm-check size-14 text-primary"
            viewBox="0 0 52 52"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <path d="M14 27l8.5 8.5L38 19" />
          </svg>

          <p className="display-2 mt-6">درخواست شما ثبت شد</p>

          <p className="mt-3 text-sm text-muted-foreground">
            «{submittedTicket.title}» با شمارهٔ {submittedTicket.id} برای هتل
            ارسال شد و به‌زودی بررسی می‌شود.
          </p>

          <span className="mt-6 h-px w-10 bg-accent" aria-hidden="true" />
        </div>
      </main>
    );
  }

  return (
    <main className="mx-auto flex w-full max-w-lg flex-1 flex-col gap-4 py-2">
      <Button asChild variant="ghost" size="sm" className="w-fit gap-1.5">
        <Link href="/guest">
          <ArrowRight className="size-3.5" />
          بازگشت
        </Link>
      </Button>

      <Card className="py-8">
        <CardHeader className="gap-2">
          <CardTitle className="display-2 rule-accent">ثبت درخواست جدید</CardTitle>
          <CardDescription className="pt-2">
            درخواست خود را برای هتل ثبت کنید.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {quickTemplates.length > 0 && (
            <div className="mb-4 flex flex-col gap-1.5">
              <span className="text-xs text-muted-foreground">درخواست سریع</span>
              <div className="flex flex-wrap gap-2">
                {quickTemplates.map((template) => (
                  <button
                    key={template.id}
                    type="button"
                    onClick={() => applyQuickTemplate(template)}
                    className="flex flex-col items-center gap-1.5 rounded-none border bg-card px-4 py-3 text-xs transition-colors hover:border-accent hover:bg-secondary/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    <QuickTemplateIcon name={template.icon} />
                    {template.title}
                  </button>
                ))}
              </div>
            </div>
          )}

          {isLoadingOptions && (
            <p className="text-sm text-muted-foreground">در حال بارگذاری…</p>
          )}

          {!isLoadingOptions && optionsError && <FormError message={optionsError} />}

          {!isLoadingOptions && !optionsError && (departments.length === 0 || categories.length === 0) && (
            <FormError
              message={
                departments.length === 0 && categories.length === 0
                  ? "هیچ واحد و دسته‌بندی‌ای در سیستم تعریف نشده است. ابتدا از پنل مدیریت اضافه کنید."
                  : departments.length === 0
                    ? "هیچ واحدی در سیستم تعریف نشده است. ابتدا از پنل مدیریت اضافه کنید."
                    : "هیچ دسته‌بندی‌ای در سیستم تعریف نشده است. ابتدا از پنل مدیریت اضافه کنید."
              }
            />
          )}

          {!isLoadingOptions && !optionsError && departments.length > 0 && categories.length > 0 && (
            <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="title">عنوان</Label>
                <Input
                  id="title"
                  placeholder="مثلاً درخواست حوله اضافه"
                  aria-invalid={!!errors.title}
                  {...register("title")}
                />
                {errors.title && (
                  <span className="text-xs text-destructive">{errors.title.message}</span>
                )}
              </div>

              <div className="flex flex-col gap-1.5">
                <Label htmlFor="description">توضیحات</Label>
                <Textarea
                  id="description"
                  placeholder="جزئیات درخواست خود را بنویسید"
                  aria-invalid={!!errors.description}
                  {...register("description")}
                />
                {errors.description && (
                  <span className="text-xs text-destructive">
                    {errors.description.message}
                  </span>
                )}
              </div>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div className="flex flex-col gap-1.5">
                  <Label>واحد مربوطه</Label>
                  <Controller
                    name="department"
                    control={control}
                    render={({ field }) => (
                      <Select onValueChange={field.onChange} value={field.value}>
                        <SelectTrigger aria-invalid={!!errors.department}>
                          <SelectValue placeholder="انتخاب واحد" />
                        </SelectTrigger>
                        <SelectContent>
                          {departments.map((dept) => (
                            <SelectItem key={dept.id} value={String(dept.id)}>
                              {dept.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    )}
                  />
                  {errors.department && (
                    <span className="text-xs text-destructive">
                      {errors.department.message}
                    </span>
                  )}
                </div>

                <div className="flex flex-col gap-1.5">
                  <Label>دسته‌بندی</Label>
                  <Controller
                    name="category"
                    control={control}
                    render={({ field }) => (
                      <Select onValueChange={field.onChange} value={field.value}>
                        <SelectTrigger aria-invalid={!!errors.category}>
                          <SelectValue placeholder="انتخاب دسته‌بندی" />
                        </SelectTrigger>
                        <SelectContent>
                          {categories.map((cat) => (
                            <SelectItem key={cat.id} value={String(cat.id)}>
                              {cat.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    )}
                  />
                  {errors.category && (
                    <span className="text-xs text-destructive">
                      {errors.category.message}
                    </span>
                  )}
                  {selectedCategory && (
                    <span className="text-xs text-muted-foreground">
                      زمان تقریبی پاسخ: {formatEstimatedResponse(selectedCategory.sla_minutes)}
                    </span>
                  )}
                </div>
              </div>

              <div className="flex flex-col gap-1.5">
                <Label>اولویت</Label>
                <Controller
                  name="priority"
                  control={control}
                  render={({ field }) => (
                    <Select onValueChange={field.onChange} value={field.value}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {priorityOptions.map((option) => (
                          <SelectItem key={option.value} value={option.value}>
                            {option.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  )}
                />
              </div>

              <div className="flex flex-col gap-1.5">
                <Label htmlFor="attachment">عکس خرابی (اختیاری)</Label>
                <label
                  htmlFor="attachment"
                  className="flex cursor-pointer items-center gap-2 rounded-md border border-dashed px-3 py-2 text-sm text-muted-foreground transition-colors hover:bg-secondary/40"
                >
                  <ImagePlus className="size-4 shrink-0" />
                  {attachmentFile ? attachmentFile.name : "انتخاب تصویر…"}
                </label>
                <input
                  id="attachment"
                  type="file"
                  accept="image/*"
                  className="sr-only"
                  onChange={(e) => {
                    setAttachmentError(null);
                    setAttachmentFile(e.target.files?.[0] ?? null);
                  }}
                />
                {attachmentError && (
                  <span className="text-xs text-destructive">{attachmentError}</span>
                )}
              </div>

              <FormError message={apiError} />

              <Button type="submit" disabled={isSubmitting} className="mt-2 gap-2">
                <Send className="size-4" />
                {isSubmitting ? "در حال ثبت…" : "ثبت درخواست"}
              </Button>
            </form>
          )}
        </CardContent>
      </Card>
    </main>
  );
}
