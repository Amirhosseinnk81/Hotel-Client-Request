"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { DoorOpen } from "lucide-react";

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

const guestLoginSchema = z.object({
  nationalId: z.string().min(1, "کد ملی را وارد کنید"),
  roomNumber: z.string().min(1, "شماره اتاق را وارد کنید"),
});

type GuestLoginForm = z.infer<typeof guestLoginSchema>;

export default function GuestLoginPage() {
  const { loginAsGuest } = useAuth();
  const router = useRouter();
  const [apiError, setApiError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<GuestLoginForm>({
    resolver: zodResolver(guestLoginSchema),
  });

  const onSubmit = async (data: GuestLoginForm) => {
    setApiError(null);
    try {
      await loginAsGuest(data.nationalId, data.roomNumber);
      router.push("/guest");
    } catch (error) {
      if (error instanceof ApiError) {
        setApiError(error.message);
      } else {
        setApiError("خطایی رخ داد. لطفاً دوباره تلاش کنید.");
      }
    }
  };

  return (
    <main className="flex min-h-full flex-1 items-center justify-center p-6">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <div className="mb-2 flex size-10 items-center justify-center rounded-full bg-primary/10 text-primary">
            <DoorOpen className="size-5" />
          </div>
          <CardTitle className="text-xl">ورود مهمان</CardTitle>
          <CardDescription>
            برای ورود، کد ملی و شماره اتاق خود را وارد کنید.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="nationalId">کد ملی</Label>
              <Input
                id="nationalId"
                inputMode="numeric"
                autoComplete="off"
                aria-invalid={!!errors.nationalId}
                {...register("nationalId")}
              />
              {errors.nationalId && (
                <span className="text-xs text-destructive">
                  {errors.nationalId.message}
                </span>
              )}
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="roomNumber">شماره اتاق</Label>
              <Input
                id="roomNumber"
                inputMode="numeric"
                autoComplete="off"
                aria-invalid={!!errors.roomNumber}
                {...register("roomNumber")}
              />
              {errors.roomNumber && (
                <span className="text-xs text-destructive">
                  {errors.roomNumber.message}
                </span>
              )}
            </div>

            <FormError message={apiError} />

            <Button type="submit" disabled={isSubmitting} className="mt-2">
              {isSubmitting ? "در حال ورود…" : "ورود"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </main>
  );
}
