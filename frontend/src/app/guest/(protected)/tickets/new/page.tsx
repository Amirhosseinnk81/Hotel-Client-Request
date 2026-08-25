"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { ArrowRight, Send } from "lucide-react";

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
import { priorityLabels } from "@/lib/ticket-labels";
import {
  ApiError,
  createTicket,
  getCategories,
  getDepartments,
} from "@/lib/api/client";
import type { Category, Department, TicketPriority } from "@/lib/api/types";

const priorityOptions: { value: TicketPriority; label: string }[] = (
  Object.keys(priorityLabels) as TicketPriority[]
).map((value) => ({ value, label: priorityLabels[value] }));

const newTicketSchema = z.object({
  title: z.string().min(3, "عنوان باید حداقل ۳ حرف باشد"),
  description: z.string().min(5, "توضیحات باید حداقل ۵ حرف باشد"),
  department: z.string().min(1, "واحد را انتخاب کنید"),
  category: z.string().min(1, "دسته‌بندی را انتخاب کنید"),
  priority: z.enum(["LOW", "NORMAL", "HIGH", "URGENT"]),
});

type NewTicketForm = z.infer<typeof newTicketSchema>;

export default function NewTicketPage() {
  const router = useRouter();
  const [departments, setDepartments] = useState<Department[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [isLoadingOptions, setIsLoadingOptions] = useState(true);
  const [optionsError, setOptionsError] = useState<string | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);

  const {
    register,
    control,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<NewTicketForm>({
    resolver: zodResolver(newTicketSchema),
    defaultValues: { title: "", description: "", department: "", category: "", priority: "NORMAL" },
  });

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

    return () => {
      cancelled = true;
    };
  }, []);

  const onSubmit = async (data: NewTicketForm) => {
    setApiError(null);
    try {
      await createTicket({
        title: data.title,
        description: data.description,
        department: Number(data.department),
        category: Number(data.category),
        priority: data.priority,
      });
      router.push("/guest/tickets");
    } catch (error) {
      setApiError(error instanceof ApiError ? error.message : "خطایی رخ داد. لطفاً دوباره تلاش کنید.");
    }
  };

  return (
    <main className="mx-auto flex w-full max-w-lg flex-1 flex-col gap-4">
      <Button asChild variant="ghost" size="sm" className="w-fit gap-1.5">
        <Link href="/guest">
          <ArrowRight className="size-3.5" />
          بازگشت
        </Link>
      </Button>

      <Card>
        <CardHeader>
          <CardTitle className="text-xl">ثبت درخواست جدید</CardTitle>
          <CardDescription>درخواست خود را برای هتل ثبت کنید.</CardDescription>
        </CardHeader>
        <CardContent>
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
