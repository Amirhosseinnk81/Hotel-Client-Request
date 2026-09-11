import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  formatDateOnly,
  formatDateTime,
  formatDurationMinutes,
  formatNumber,
  formatRelativeTime,
} from "./format";

describe("formatNumber", () => {
  it("renders Persian digits", () => {
    expect(formatNumber(0)).toBe("۰");
    expect(formatNumber(42)).toBe("۴۲");
  });
});

describe("formatDurationMinutes", () => {
  it("keeps short spans in minutes", () => {
    expect(formatDurationMinutes(25)).toBe("۲۵ دقیقه");
  });

  it("rounds to whole minutes", () => {
    expect(formatDurationMinutes(30.4)).toBe("۳۰ دقیقه");
  });

  it("switches to hours, dropping a zero minute part", () => {
    expect(formatDurationMinutes(60)).toBe("۱ ساعت");
    expect(formatDurationMinutes(96)).toBe("۱ ساعت و ۳۶ دقیقه");
  });

  it("switches to days and drops minutes once days are involved", () => {
    expect(formatDurationMinutes(1440)).toBe("۱ روز");
    expect(formatDurationMinutes(1500)).toBe("۱ روز و ۱ ساعت");
    expect(formatDurationMinutes(1441)).toBe("۱ روز");
  });

  it("never goes negative", () => {
    expect(formatDurationMinutes(-5)).toBe("۰ دقیقه");
  });
});

describe("formatDateOnly / formatDateTime", () => {
  it("renders a Persian calendar date", () => {
    expect(formatDateOnly("2026-03-21T10:00:00Z")).toContain("۱۴۰۵");
  });

  it("includes the time of day", () => {
    const withTime = formatDateTime("2026-03-21T10:00:00Z");
    const dateOnly = formatDateOnly("2026-03-21T10:00:00Z");
    expect(withTime.length).toBeGreaterThan(dateOnly.length);
  });
});

describe("formatRelativeTime", () => {
  const NOW = new Date("2026-06-15T12:00:00Z");

  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(NOW);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("shows 'اکنون' for moments within the last ~45 seconds", () => {
    expect(formatRelativeTime(new Date(NOW.getTime() - 10_000).toISOString())).toBe("اکنون");
  });

  it("shows minutes ago for a recent timestamp", () => {
    expect(formatRelativeTime(new Date(NOW.getTime() - 5 * 60_000).toISOString())).toBe(
      "۵ دقیقه پیش"
    );
  });

  it("shows hours ago for same-day timestamps", () => {
    expect(formatRelativeTime(new Date(NOW.getTime() - 3 * 3_600_000).toISOString())).toBe(
      "۳ ساعت پیش"
    );
  });

  it("shows 'دیروز' for yesterday", () => {
    expect(formatRelativeTime(new Date(NOW.getTime() - 25 * 3_600_000).toISOString())).toBe(
      "دیروز"
    );
  });

  it("handles future timestamps (e.g. an SLA due time) the same way, in reverse", () => {
    expect(formatRelativeTime(new Date(NOW.getTime() + 5 * 60_000).toISOString())).toBe(
      "۵ دقیقه بعد"
    );
  });
});
