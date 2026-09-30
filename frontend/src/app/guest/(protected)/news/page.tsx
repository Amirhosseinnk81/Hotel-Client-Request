"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight } from "lucide-react";

import { Button } from "@/components/ui/button";
import { FormError } from "@/components/form-error";
import { NewsList } from "@/components/news-list";
import { useLocale } from "@/contexts/locale-context";
import { ApiError, getGuestNews } from "@/lib/api/client";
import type { NewsItem } from "@/lib/api/types";

/**
 * What the hotel is telling its guests — tonight's live music, the pool
 * closing for cleaning. Written in Django Admin; what is on screen is
 * decided by each item's publish window, so nobody has to remember to
 * take yesterday's event down.
 *
 * The same items reach the in-room television (apps/iptv), through the
 * same helper, so the two can't disagree.
 */
export default function GuestNewsPage() {
  const { t } = useLocale();
  const [items, setItems] = useState<NewsItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getGuestNews()
      .then((rows) => {
        if (!cancelled) setItems(rows);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : t("news.loadError"));
        }
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- t only changes the fallback text
  }, []);

  return (
    <main className="mx-auto flex w-full max-w-lg flex-1 flex-col gap-4">
      <Button asChild variant="ghost" size="sm" className="w-fit gap-1.5">
        <Link href="/guest">
          <ArrowRight className="size-3.5 ltr:rotate-180" />
          {t("common.back")}
        </Link>
      </Button>

      <div>
        <h1 className="display-2 rule-accent">{t("news.title")}</h1>
        <p className="pt-2 text-sm text-muted-foreground">{t("news.subtitle")}</p>
      </div>

      {error && <FormError message={error} />}
      {!error && <NewsList items={items} />}
    </main>
  );
}
