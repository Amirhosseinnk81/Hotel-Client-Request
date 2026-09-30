"use client";

import type { ComponentType } from "react";
import { Megaphone } from "lucide-react";
import * as LucideIcons from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useOptionalLocale } from "@/contexts/locale-context";
import type { NewsItem } from "@/lib/api/types";
import { formatDateTime } from "@/lib/format";

/** A NewsItem.icon (a lucide-react name), falling back to Megaphone. */
function NewsIcon({ name }: { name: string }) {
  const Icon = (LucideIcons as unknown as Record<string, ComponentType<{ className?: string }>>)[
    name
  ];
  const Resolved = Icon ?? Megaphone;
  return <Resolved className="size-5 text-primary" />;
}

/**
 * The hotel's announcements, rendered the same way for a guest and for
 * an operator — the difference between the two audiences is which
 * endpoint filled `items` (apps/news has one per audience), not how a
 * notice looks.
 *
 * Bilingual through `useOptionalLocale`: inside the guest portal the
 * English text is used when the hotel filled it in, and in the operator
 * panel it is always Persian.
 */
export function NewsList({ items }: { items: NewsItem[] | null }) {
  const { t, locale } = useOptionalLocale();
  const pick = (fa: string, en: string) => (locale === "en" && en.trim() ? en : fa);

  if (!items) {
    return (
      <div className="flex flex-col gap-3">
        {[0, 1, 2].map((i) => (
          <Card key={i}>
            <CardHeader>
              <Skeleton className="h-5 w-48" />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-4 w-full" />
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  if (items.length === 0) {
    return <p className="text-sm text-muted-foreground">{t("news.empty")}</p>;
  }

  return (
    <div className="flex flex-col gap-3">
      {items.map((item) => (
        <Card key={item.id}>
          <CardHeader className="flex-row items-start gap-3 space-y-0">
            <NewsIcon name={item.icon} />
            <div className="flex-1">
              <CardTitle className="text-base font-medium">
                {pick(item.title, item.title_en)}
              </CardTitle>
              {(item.event_at || item.location) && (
                <p className="pt-1 text-xs text-muted-foreground">
                  {item.event_at && formatDateTime(item.event_at, locale)}
                  {item.event_at && item.location && " — "}
                  {item.location}
                </p>
              )}
            </div>
            {item.kind === "EVENT" && (
              <Badge variant="secondary" className="text-[11px] font-normal">
                {t("news.event")}
              </Badge>
            )}
          </CardHeader>
          <CardContent>
            {/* Line breaks as typed in Django Admin. */}
            <p className="whitespace-pre-wrap text-sm text-muted-foreground">
              {pick(item.body, item.body_en)}
            </p>
            {item.department_name && (
              <p className="pt-2 text-xs text-muted-foreground">{item.department_name}</p>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
