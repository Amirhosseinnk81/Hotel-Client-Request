"use client";

import { useEffect, useState, type ComponentType } from "react";
import Link from "next/link";
import { ArrowRight, Info } from "lucide-react";
import * as LucideIcons from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { FormError } from "@/components/form-error";
import { useLocale } from "@/contexts/locale-context";
import { ApiError, getHotelInfo } from "@/lib/api/client";
import type { HotelInfo } from "@/lib/api/types";

/** A HotelInfo.icon (a lucide-react name), falling back to Info. */
function InfoIcon({ name }: { name: string }) {
  const Icon = (LucideIcons as unknown as Record<string, ComponentType<{ className?: string }>>)[name];
  const Resolved = Icon ?? Info;
  return <Resolved className="size-5 text-primary" />;
}

/**
 * The guest help page (inspired by Odoo Helpdesk's help center): Wi-Fi,
 * breakfast hours, check-out time — so a guest finds the answer instead of
 * filing a ticket. Entries come from Django Admin (Hotel info); in English
 * the English text is shown when the hotel filled it in, else the Persian.
 */
export default function GuestHotelInfoPage() {
  const { t, locale } = useLocale();
  const [entries, setEntries] = useState<HotelInfo[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getHotelInfo()
      .then((rows) => {
        if (!cancelled) setEntries(rows);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof ApiError ? err.message : t("info.loadError"));
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- t only changes the fallback text
  }, []);

  const pick = (fa: string, en: string) => (locale === "en" && en.trim() ? en : fa);

  return (
    <main className="mx-auto flex w-full max-w-lg flex-1 flex-col gap-4">
      <Button asChild variant="ghost" size="sm" className="w-fit gap-1.5">
        <Link href="/guest">
          <ArrowRight className="size-3.5 ltr:rotate-180" />
          {t("common.back")}
        </Link>
      </Button>

      <div>
        <h1 className="display-2 rule-accent">{t("info.title")}</h1>
        <p className="pt-2 text-sm text-muted-foreground">{t("info.subtitle")}</p>
      </div>

      {error && <FormError message={error} />}

      {!entries && !error &&
        [0, 1, 2].map((i) => (
          <Card key={i}>
            <CardHeader>
              <Skeleton className="h-5 w-40" />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-4 w-full" />
            </CardContent>
          </Card>
        ))}

      {entries && entries.length === 0 && (
        <p className="text-sm text-muted-foreground">{t("info.empty")}</p>
      )}

      {entries?.map((entry) => (
        <Card key={entry.id}>
          <CardHeader className="flex-row items-center gap-3 space-y-0">
            <InfoIcon name={entry.icon} />
            <CardTitle className="text-base font-medium">{pick(entry.title, entry.title_en)}</CardTitle>
          </CardHeader>
          <CardContent>
            {/* Line breaks as typed in the admin (e.g. network name / password). */}
            <p className="whitespace-pre-line text-sm">{pick(entry.body, entry.body_en)}</p>
          </CardContent>
        </Card>
      ))}
    </main>
  );
}
