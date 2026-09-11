/**
 * Centralized date/time formatting — Stage 2.5. Previously every page that
 * showed a ticket date (`operator/page.tsx`, `guest/tickets/page.tsx`,
 * both `[id]/page.tsx` detail pages) defined its own local `formatDate`,
 * so the exact same `Intl.DateTimeFormat` options were copy-pasted four
 * times. Consolidated here, plus the new relative-time formatter that
 * powers `<RelativeTime />`.
 */

const dateOnlyFormatter = new Intl.DateTimeFormat("fa-IR", {
  year: "numeric",
  month: "long",
  day: "numeric",
});

const dateTimeFormatter = new Intl.DateTimeFormat("fa-IR", {
  year: "numeric",
  month: "long",
  day: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

/** e.g. "۱۲ شهریور ۱۴۰۵" — used where only the day matters (list cards). */
export function formatDateOnly(iso: string): string {
  return dateOnlyFormatter.format(new Date(iso));
}

/** e.g. "۱۲ شهریور ۱۴۰۵ ساعت ۱۴:۳۰" — used on detail pages. */
export function formatDateTime(iso: string): string {
  return dateTimeFormatter.format(new Date(iso));
}

const RELATIVE_UNITS: { unit: Intl.RelativeTimeFormatUnit; seconds: number }[] = [
  { unit: "year", seconds: 31536000 },
  { unit: "month", seconds: 2592000 },
  { unit: "week", seconds: 604800 },
  { unit: "day", seconds: 86400 },
  { unit: "hour", seconds: 3600 },
  { unit: "minute", seconds: 60 },
];

const relativeFormatter = new Intl.RelativeTimeFormat("fa", { numeric: "auto" });

/**
 * "۲ ساعت پیش" / "دیروز" / "اکنون" — always paired with a tooltip showing
 * the exact `formatDateTime` value (see `<RelativeTime />`), never used
 * alone, since a relative string alone can't be scanned precisely.
 */
export function formatRelativeTime(iso: string): string {
  const diffSeconds = (new Date(iso).getTime() - Date.now()) / 1000;
  const abs = Math.abs(diffSeconds);

  if (abs < 45) return "اکنون";

  for (const { unit, seconds } of RELATIVE_UNITS) {
    if (abs >= seconds) {
      const value = Math.round(diffSeconds / seconds);
      return relativeFormatter.format(value, unit);
    }
  }

  return relativeFormatter.format(Math.round(diffSeconds / 60), "minute");
}

const numberFormatter = new Intl.NumberFormat("fa-IR");

/** e.g. 42 -> "۴۲" — counts on the stats summary. */
export function formatNumber(value: number): string {
  return numberFormatter.format(value);
}

/**
 * A span of minutes in words: 25 -> "۲۵ دقیقه", 96 -> "۱ ساعت و ۳۶ دقیقه",
 * 1500 -> "۱ روز و ۱ ساعت". Rounds to whole minutes, and drops minutes
 * once days are involved — "۳ روز و ۴ ساعت و ۱۲ دقیقه" is more precision
 * than an average resolution time deserves.
 */
export function formatDurationMinutes(minutes: number): string {
  const total = Math.max(0, Math.round(minutes));
  const days = Math.floor(total / 1440);
  const hours = Math.floor((total % 1440) / 60);
  const mins = total % 60;

  if (days > 0) {
    return hours > 0
      ? `${formatNumber(days)} روز و ${formatNumber(hours)} ساعت`
      : `${formatNumber(days)} روز`;
  }
  if (hours > 0) {
    return mins > 0
      ? `${formatNumber(hours)} ساعت و ${formatNumber(mins)} دقیقه`
      : `${formatNumber(hours)} ساعت`;
  }
  return `${formatNumber(mins)} دقیقه`;
}
