import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { formatDateTime, formatRelativeTime } from "@/lib/format";
import { cn } from "@/lib/utils";

/**
 * Stage 2.5 — shows "۲ ساعت پیش" instead of a raw date, with the exact
 * date/time available on hover/focus (and via `title` as a no-JS/no-hover
 * fallback, e.g. on touch). Used everywhere a ticket timestamp is shown.
 */
export function RelativeTime({ iso, className }: { iso: string; className?: string }) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span
          className={cn("cursor-default underline decoration-dotted underline-offset-2", className)}
          title={formatDateTime(iso)}
        >
          {formatRelativeTime(iso)}
        </span>
      </TooltipTrigger>
      <TooltipContent>{formatDateTime(iso)}</TooltipContent>
    </Tooltip>
  );
}
