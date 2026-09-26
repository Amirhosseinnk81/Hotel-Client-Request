"use client";

import { Star } from "lucide-react";

import { useOptionalLocale } from "@/contexts/locale-context";

/**
 * Stars, shared by every rating surface: a guest scoring a resolved
 * ticket and a department scoring the work IT did for them.
 *
 * `useOptionalLocale` for the same reason as RelativeTime and the PDF
 * button — inside the guest portal the labels follow the guest's
 * language, and in the operator panel (Persian only) they fall back to
 * Persian.
 *
 * `dir="ltr"` on the row is deliberate: one star through five reads
 * left-to-right even on an RTL page, the way every rating widget does.
 */

export function StarPicker({
  value,
  onChange,
  disabled = false,
}: {
  value: number;
  onChange: (n: number) => void;
  disabled?: boolean;
}) {
  const { t } = useOptionalLocale();
  return (
    <div className="flex gap-1" dir="ltr">
      {[1, 2, 3, 4, 5].map((n) => (
        <button
          key={n}
          type="button"
          disabled={disabled}
          onClick={() => onChange(n)}
          className="rounded-sm outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50"
          aria-label={t("detail.star", { n })}
        >
          <Star
            className={
              n <= value ? "size-6 fill-warning text-warning" : "size-6 text-muted-foreground"
            }
          />
        </button>
      ))}
    </div>
  );
}

/** Read-only stars, once a rating already exists. */
export function StarDisplay({ value, className = "size-5" }: { value: number; className?: string }) {
  return (
    <div className="flex gap-1" dir="ltr">
      {[1, 2, 3, 4, 5].map((n) => (
        <Star
          key={n}
          className={
            n <= value ? `${className} fill-warning text-warning` : `${className} text-muted-foreground`
          }
        />
      ))}
    </div>
  );
}
