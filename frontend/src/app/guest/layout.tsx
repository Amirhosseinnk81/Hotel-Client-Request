"use client";

import { LocaleProvider } from "@/contexts/locale-context";

/**
 * Everything under /guest (login included) can be shown in English as
 * well as Persian; the operator panel stays Persian. See
 * contexts/locale-context.tsx and lib/i18n.ts.
 */
export default function GuestRootLayout({ children }: { children: React.ReactNode }) {
  return <LocaleProvider>{children}</LocaleProvider>;
}
