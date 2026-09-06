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
    // Brand moment: generous vertical air and a wider card than a
    // utilitarian login would use. This is the first screen a guest
    // sees, so it carries the hotel's identity rather than optimising
    // for density.
    <main className="flex min-h-full flex-1 items-center justify-center px-6 py-16">
      <Card className="w-full max-w-md px-2 py-10">
        <CardHeader className="gap-3">
          <div className="mb-1 flex size-11 items-center justify-center border border-accent/40 text-accent">
            <DoorOpen className="size-5" />
          </div>
          <CardTitle className="display-2 rule-accent">ورود مهمان</CardTitle>
          <CardDescription className="pt-2">
            برای ورود، کد ملی و شماره اتاق خود را وارد کنید.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-5">
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

            <Button type="submit" disabled={isSubmitting} className="mt-3 w-full">
              {isSubmitting ? "در حال ورود…" : "ورود"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </main>
  );
}
