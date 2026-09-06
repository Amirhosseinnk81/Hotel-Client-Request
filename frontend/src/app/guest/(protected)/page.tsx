"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { BedDouble, FilePlus2, IdCard, ListChecks, Phone, User } from "lucide-react";

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { FormError } from "@/components/form-error";
import { getGuestProfile, ApiError } from "@/lib/api/client";
import type { GuestProfile } from "@/lib/api/types";

function ProfileRow({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ElementType;
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-center gap-3 rounded-lg border bg-secondary/30 p-3">
      <Icon className="size-4 text-muted-foreground" />
      <div className="flex flex-col">
        <span className="text-xs text-muted-foreground">{label}</span>
        <span className="text-sm font-medium" dir={label === "شماره تلفن" ? "ltr" : undefined}>
          {value}
        </span>
      </div>
    </div>
  );
}

export default function GuestDashboardPage() {
  const [profile, setProfile] = useState<GuestProfile | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    getGuestProfile()
      .then((data) => {
        if (!cancelled) setProfile(data);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof ApiError ? err.message : "خطا در دریافت اطلاعات پروفایل.");
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-6">
      <div>
        <h1 className="display-2">خوش آمدید{profile ? `، ${profile.full_name}` : ""}</h1>
        <p className="text-sm text-muted-foreground">پروفایل و درخواست‌های شما</p>
      </div>

      {isLoading && (
        <Card>
          <CardContent className="pt-6 text-sm text-muted-foreground">
            در حال بارگذاری اطلاعات…
          </CardContent>
        </Card>
      )}

      {!isLoading && error && (
        <Card>
          <CardContent className="pt-6">
            <FormError message={error} />
          </CardContent>
        </Card>
      )}

      {!isLoading && profile && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base font-medium">اطلاعات مهمان</CardTitle>
            <CardDescription>اطلاعات ثبت‌شدهٔ شما نزد هتل</CardDescription>
          </CardHeader>
          <CardContent className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <ProfileRow icon={User} label="نام و نام خانوادگی" value={profile.full_name} />
            <ProfileRow icon={IdCard} label="کد ملی" value={profile.national_id} />
            <ProfileRow icon={Phone} label="شماره تلفن" value={profile.phone || "—"} />
            <ProfileRow
              icon={BedDouble}
              label="شماره اتاق"
              value={profile.room_number ?? "—"}
            />
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-base font-medium">درخواست‌ها</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3 sm:flex-row">
          <Button asChild className="flex-1 gap-2">
            <Link href="/guest/tickets/new">
              <FilePlus2 className="size-4" />
              ثبت درخواست جدید
            </Link>
          </Button>
          <Button asChild variant="outline" className="flex-1 gap-2">
            <Link href="/guest/tickets">
              <ListChecks className="size-4" />
              درخواست‌های من
            </Link>
          </Button>
        </CardContent>
      </Card>
    </main>
  );
}
