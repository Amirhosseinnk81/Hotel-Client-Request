"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import { localeDir, translate, type Locale, type MessageKey } from "@/lib/i18n";

/** localStorage key — a per-viewer convenience, like the theme choice. */
export const GUEST_LOCALE_STORAGE_KEY = "guest-locale";

interface LocaleContextValue {
  locale: Locale;
  dir: "rtl" | "ltr";
  setLocale: (locale: Locale) => void;
  t: (key: MessageKey, vars?: Record<string, string | number>) => string;
}

const LocaleContext = createContext<LocaleContextValue | null>(null);

function readStoredLocale(): Locale {
  try {
    return window.localStorage.getItem(GUEST_LOCALE_STORAGE_KEY) === "en" ? "en" : "fa";
  } catch {
    return "fa";
  }
}

/**
 * Language for the guest portal only (wraps app/guest). Switches <html>
 * lang/dir while mounted and puts them back to fa/rtl on the way out, so
 * the operator panel is never left in LTR. The root layout's init script
 * applies a stored English choice before first paint, to avoid a flash
 * of right-to-left layout for English guests.
 */
export function LocaleProvider({ children }: { children: React.ReactNode }) {
  // Server render and first client render are always "fa" (no
  // localStorage on the server); the stored choice is applied right after.
  const [locale, setLocaleState] = useState<Locale>("fa");
  // Until the stored choice has been read, leave <html> as the root
  // layout's init script set it — touching it earlier would flash RTL
  // for a guest who picked English.
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const stored = readStoredLocale();
    queueMicrotask(() => {
      setLocaleState(stored);
      setReady(true);
    });
  }, []);

  useEffect(() => {
    if (!ready) return;
    const root = document.documentElement;
    root.lang = locale;
    root.dir = localeDir(locale);
    return () => {
      root.lang = "fa";
      root.dir = "rtl";
    };
  }, [locale, ready]);

  const setLocale = useCallback((next: Locale) => {
    setLocaleState(next);
    try {
      window.localStorage.setItem(GUEST_LOCALE_STORAGE_KEY, next);
    } catch {
      // Private mode etc. — the choice just won't survive a reload.
    }
  }, []);

  const value = useMemo<LocaleContextValue>(
    () => ({
      locale,
      dir: localeDir(locale),
      setLocale,
      t: (key, vars) => translate(locale, key, vars),
    }),
    [locale, setLocale]
  );

  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>;
}

export function useLocale(): LocaleContextValue {
  const context = useContext(LocaleContext);
  if (!context) throw new Error("useLocale() must be used inside <LocaleProvider>.");
  return context;
}

/**
 * For components shared with the (Persian-only) operator panel: follows
 * the guest's language inside the guest portal, and is plain Persian
 * everywhere else.
 */
export function useOptionalLocale(): Pick<LocaleContextValue, "locale" | "t"> {
  const context = useContext(LocaleContext);
  return context ?? { locale: "fa", t: (key, vars) => translate("fa", key, vars) };
}
