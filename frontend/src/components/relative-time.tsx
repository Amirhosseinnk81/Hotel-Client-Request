"use client";

import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { useOptionalLocale } from "@/contexts/locale-context";
import { formatDateTime, formatRelativeTime } from "@/lib/format";
import { cn } from "@/lib/utils";

/**
 * Stage 2.5 — shows "۲ ساعت پیش" instead of a raw date, with the exact
 * date/time available on hover/focus (and via `title` as a no-JS/no-hover
 * fallback, e.g. on touch). Used everywhere a ticket timestamp is shown.
 * In the guest portal it follows the guest's language ("2 hours ago").
 */
export function RelativeTime({ iso, className }: { iso: string; className?: string }) {
  const { locale } = useOptionalLocale();
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span
          className={cn("cursor-default underline decoration-dotted underline-offset-2", className)}
          title={formatDateTime(iso, locale)}
        >
          {formatRelativeTime(iso, locale)}
        </span>
      </TooltipTrigger>
      <TooltipContent>{formatDateTime(iso, locale)}</TooltipContent>
    </Tooltip>
  );
}
