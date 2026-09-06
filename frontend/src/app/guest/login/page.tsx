"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
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
import { Skeleton } from "@/components/ui/skeleton";
import { FormError } from "@/components/form-error";
import { useAuth } from "@/contexts/auth-context";
import { ApiError } from "@/lib/api/client";
import { normalizeRoomParam } from "@/lib/room-param";

const guestLoginSchema = z.object({
  nationalId: z.string().min(1, "کد ملی را وارد کنید"),
  roomNumber: z.string().min(1, "شماره اتاق را وارد کنید"),
});

type GuestLoginForm = z.infer<typeof guestLoginSchema>;

/**
 * Room QR deep link: `/guest/login?room=305`.
 *
 * This is the login form, not the new-ticket form — the ticket form has
 * no room field at all (the backend derives it from the guest's
 * profile), so `?room=` would have nothing to fill there. Parsing lives
 * in lib/room-param.ts so it can be unit-tested.
 */
function GuestLoginContent() {
  const { loginAsGuest } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [apiError, setApiError] = useState<string | null>(null);

  const roomFromQr = normalizeRoomParam(searchParams.get("room"));

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<GuestLoginForm>({
    resolver: zodResolver(guestLoginSchema),
    defaultValues: { nationalId: "", roomNumber: roomFromQr },
  });

  const onSubmit = async (data: GuestLoginForm) => {
    setApiError(null);
    try {
      await loginAsGuest(data.nationalId, data.roomNumber);
      // A guest who arrived by scanning the QR in their room is there to
      // ask for something — drop them on the request form rather than
      // the dashboard they'd otherwise have to navigate through.
      router.push(roomFromQr ? "/guest/tickets/new" : "/guest");
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
            {roomFromQr
              ? `شماره اتاق ${roomFromQr} از روی کد QR وارد شد. برای ورود، کد ملی خود را هم وارد کنید.`
              : "برای ورود، کد ملی و شماره اتاق خود را وارد کنید."}
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

/**
 * useSearchParams() opts a route into client-side rendering, and the App
 * Router requires it to sit under a Suspense boundary or the whole page
 * refuses to prerender at build time. The fallback mirrors the card's
 * silhouette so the QR-scanning guest doesn't get a layout jump on a
 * hotel wifi connection.
 */
export default function GuestLoginPage() {
  return (
    <Suspense
      fallback={
        <main className="flex min-h-full flex-1 items-center justify-center px-6 py-16">
          <Card className="w-full max-w-md px-2 py-10">
            <CardHeader className="gap-3">
              <Skeleton className="size-11" />
              <Skeleton className="h-7 w-32" />
              <Skeleton className="h-4 w-56" />
            </CardHeader>
            <CardContent>
              <div className="flex flex-col gap-5">
                <Skeleton className="h-14 w-full" />
                <Skeleton className="h-14 w-full" />
                <Skeleton className="mt-3 h-10 w-full" />
              </div>
            </CardContent>
          </Card>
        </main>
      }
    >
      <GuestLoginContent />
    </Suspense>
  );
}
