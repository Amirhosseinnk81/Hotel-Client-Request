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
import { useLocale } from "@/contexts/locale-context";
import { getGuestProfile, ApiError } from "@/lib/api/client";
import type { GuestProfile } from "@/lib/api/types";

function ProfileRow({
  icon: Icon,
  label,
  value,
  ltr = false,
}: {
  icon: React.ElementType;
  label: string;
  value: string;
  ltr?: boolean;
}) {
  return (
    <div className="flex items-center gap-3 rounded-lg border bg-secondary/30 p-3">
      <Icon className="size-4 text-muted-foreground" />
      <div className="flex flex-col">
        <span className="text-xs text-muted-foreground">{label}</span>
        <span className="text-sm font-medium" dir={ltr ? "ltr" : undefined}>
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
  const { t } = useLocale();

  useEffect(() => {
    let cancelled = false;

    getGuestProfile()
      .then((data) => {
        if (!cancelled) setProfile(data);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof ApiError ? err.message : t("home.profileError"));
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- t only changes the fallback text
  }, []);

  return (
    <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-6">
      <div>
        <h1 className="display-2">
          {profile ? t("home.welcomeName", { name: profile.full_name }) : t("home.welcome")}
        </h1>
        <p className="text-sm text-muted-foreground">{t("home.subtitle")}</p>
      </div>

      {isLoading && (
        <Card>
          <CardContent className="pt-6 text-sm text-muted-foreground">
            {t("home.loadingProfile")}
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
            <CardTitle className="text-base font-medium">{t("home.profileTitle")}</CardTitle>
            <CardDescription>{t("home.profileDescription")}</CardDescription>
          </CardHeader>
          <CardContent className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <ProfileRow icon={User} label={t("home.fullName")} value={profile.full_name} />
            <ProfileRow icon={IdCard} label={t("home.nationalId")} value={profile.national_id} />
            <ProfileRow icon={Phone} label={t("home.phone")} value={profile.phone || "—"} ltr />
            <ProfileRow
              icon={BedDouble}
              label={t("home.room")}
              value={profile.room_number ?? "—"}
            />
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-base font-medium">{t("home.requests")}</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3 sm:flex-row">
          <Button asChild className="flex-1 gap-2">
            <Link href="/guest/tickets/new">
              <FilePlus2 className="size-4" />
              {t("home.newRequest")}
            </Link>
          </Button>
          <Button asChild variant="outline" className="flex-1 gap-2">
            <Link href="/guest/tickets">
              <ListChecks className="size-4" />
              {t("home.myRequests")}
            </Link>
          </Button>
        </CardContent>
      </Card>
    </main>
  );
}
