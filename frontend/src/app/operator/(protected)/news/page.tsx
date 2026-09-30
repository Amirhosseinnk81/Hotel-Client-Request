"use client";

import { useEffect, useState } from "react";

import { FormError } from "@/components/form-error";
import { NewsList } from "@/components/news-list";
import { ApiError, getOperatorNews } from "@/lib/api/client";
import type { NewsItem } from "@/lib/api/types";

/**
 * Staff announcements — the shift briefing, a VIP arriving, the pool
 * closing. Hotel-wide items plus this operator's own department's;
 * written in Django Admin, and on screen only while inside its publish
 * window.
 *
 * Guest news is a separate endpoint on purpose (apps/news/views.py), so
 * nothing here can ever be widened onto a guest's phone.
 */
export default function OperatorNewsPage() {
  const [items, setItems] = useState<NewsItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getOperatorNews()
      .then((rows) => {
        if (!cancelled) setItems(rows);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : "خطا در دریافت اخبار.");
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-4">
      <div>
        <h1 className="display-2 rule-accent">اخبار و اطلاعیه‌ها</h1>
        <p className="pt-2 text-sm text-muted-foreground">
          اطلاعیه‌های کل هتل و واحد شما. ثبت و ویرایش در پنل مدیریت جنگو انجام می‌شود.
        </p>
      </div>

      {error && <FormError message={error} />}
      {!error && <NewsList items={items} />}
    </main>
  );
}
