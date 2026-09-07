"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Briefcase } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { FormError } from "@/components/form-error";
import { useAuth } from "@/contexts/auth-context";
import { ApiError } from "@/lib/api/client";

const operatorLoginSchema = z.object({
  username: z.string().min(1, "نام کاربری را وارد کنید"),
  password: z.string().min(1, "رمز عبور را وارد کنید"),
});

type OperatorLoginForm = z.infer<typeof operatorLoginSchema>;

export default function OperatorLoginPage() {
  const { loginAsOperator } = useAuth();
  const router = useRouter();
  const [apiError, setApiError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<OperatorLoginForm>({
    resolver: zodResolver(operatorLoginSchema),
  });

  const onSubmit = async (data: OperatorLoginForm) => {
    setApiError(null);
    try {
      await loginAsOperator(data.username, data.password);
      router.push("/operator");
    } catch (error) {
      setApiError(
        error instanceof ApiError ? error.message : "خطایی رخ داد. لطفاً دوباره تلاش کنید."
      );
    }
  };

  return (
    <main className="flex min-h-full flex-1 items-center justify-center px-6 py-16">
      <Card className="w-full max-w-md px-2 py-10">
        <CardHeader className="gap-3">
          <div className="mb-1 flex size-11 items-center justify-center border border-accent/40 text-accent">
            <Briefcase className="size-5" />
          </div>
          <CardTitle className="display-2 rule-accent">ورود اپراتور</CardTitle>
          <CardDescription className="pt-2">
            با نام کاربری و رمز عبور خود وارد شوید.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-5">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="username">نام کاربری</Label>
              <Input
                id="username"
                autoComplete="username"
                aria-invalid={!!errors.username}
                {...register("username")}
              />
              {errors.username && (
                <span className="text-xs text-destructive">
                  {errors.username.message}
                </span>
              )}
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="password">رمز عبور</Label>
              <Input
                id="password"
                type="password"
                autoComplete="current-password"
                aria-invalid={!!errors.password}
                {...register("password")}
              />
              {errors.password && (
                <span className="text-xs text-destructive">
                  {errors.password.message}
                </span>
              )}
            </div>

            <FormError message={apiError} />

            <Button type="submit" disabled={isSubmitting} className="mt-3 w-full">
              {isSubmitting ? "در حال ورود…" : "ورود"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </main>
  );
}
