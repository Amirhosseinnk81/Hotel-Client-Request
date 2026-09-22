import { describe, expect, it } from "vitest";

import { formatNumber, formatRelativeTime } from "./format";
import { localeDir, messages, translate, type MessageKey } from "./i18n";

const placeholders = (text: string) => [...text.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort();

describe("guest translations", () => {
  it("has every key in both languages", () => {
    expect(Object.keys(messages.en).sort()).toEqual(Object.keys(messages.fa).sort());
  });

  it("uses the same {placeholders} in both languages", () => {
    for (const key of Object.keys(messages.fa) as MessageKey[]) {
      expect(placeholders(messages.en[key]), key).toEqual(placeholders(messages.fa[key]));
    }
  });

  it("never leaves an English string empty", () => {
    for (const [key, value] of Object.entries(messages.en)) {
      expect(value.trim(), key).not.toBe("");
    }
  });

  it("fills placeholders", () => {
    expect(translate("en", "home.welcomeName", { name: "Sara" })).toBe("Welcome, Sara");
    expect(translate("fa", "new.hoursMinutes", { h: 1, m: 30 })).toBe("1 ساعت و 30 دقیقه");
  });

  it("leaves an unknown placeholder visible rather than blank", () => {
    expect(translate("en", "home.welcomeName")).toBe("Welcome, {name}");
  });

  it("maps languages to text direction", () => {
    expect(localeDir("fa")).toBe("rtl");
    expect(localeDir("en")).toBe("ltr");
  });
});

describe("locale-aware formatting", () => {
  it("uses Latin digits in English and Persian digits by default", () => {
    expect(formatNumber(42, "en")).toBe("42");
    expect(formatNumber(42)).toBe("۴۲");
  });

  it("says 'just now' in English", () => {
    expect(formatRelativeTime(new Date().toISOString(), "en")).toBe("just now");
    expect(formatRelativeTime(new Date().toISOString())).toBe("اکنون");
  });
});
