"use client";

import { Suspense, useMemo, useState } from "react";
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
import { LanguageSwitcher } from "@/components/language-switcher";
import { useAuth } from "@/contexts/auth-context";
import { useLocale } from "@/contexts/locale-context";
import { ApiError } from "@/lib/api/client";
import { normalizeRoomParam } from "@/lib/room-param";

type GuestLoginForm = { nationalId: string; roomNumber: string };

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
  const { t, locale } = useLocale();

  // Built per language so the validation messages follow the switcher.
  const guestLoginSchema = useMemo(
    () =>
      z.object({
        nationalId: z.string().min(1, t("login.nationalIdRequired")),
        roomNumber: z.string().min(1, t("login.roomNumberRequired")),
      }),
    [t]
  );

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
        setApiError(t("common.genericError"));
      }
    }
  };

  return (
    // Brand moment: generous vertical air and a wider card than a
    // utilitarian login would use. This is the first screen a guest
    // sees, so it carries the hotel's identity rather than optimising
    // for density.
    <main className="relative flex min-h-full flex-1 items-center justify-center px-6 py-16">
      <div className="absolute end-4 top-4">
        <LanguageSwitcher />
      </div>
      <Card className="w-full max-w-md px-2 py-10">
        <CardHeader className="gap-3">
          <div className="mb-1 flex size-11 items-center justify-center border border-accent/40 text-accent">
            <DoorOpen className="size-5" />
          </div>
          <CardTitle className="display-2 rule-accent">{t("login.title")}</CardTitle>
          <CardDescription className="pt-2">
            {roomFromQr
              ? t("login.descriptionFromQr", { room: roomFromQr })
              : t("login.description")}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-5">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="nationalId">{t("login.nationalId")}</Label>
              <Input
                id="nationalId"
                inputMode={locale === "fa" ? "numeric" : "text"}
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
              <Label htmlFor="roomNumber">{t("login.roomNumber")}</Label>
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
              {isSubmitting ? t("login.submitting") : t("login.submit")}
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
