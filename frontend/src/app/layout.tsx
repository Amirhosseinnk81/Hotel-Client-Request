import type { Metadata } from "next";
import "@fontsource-variable/vazirmatn";
import "./globals.css";

import { AuthProvider } from "@/contexts/auth-context";
import { ThemeProvider } from "@/contexts/theme-context";
import { Toaster } from "@/components/toaster";

export const metadata: Metadata = {
  title: "پلتفرم درخواست‌های مهمان هتل",
  description: "سامانه مدیریت درخواست‌های مهمانان هتل",
};

// Stage 2.7 — runs before React hydrates so the very first paint already
// has the right theme class (otherwise there's a flash of light mode
// for anyone who has dark mode saved). Reads the same source of truth
// ThemeProvider uses: an explicit localStorage choice, falling back to
// the OS-level prefers-color-scheme.
const THEME_INIT_SCRIPT = `
  (function () {
    try {
      var stored = window.localStorage.getItem("theme");
      var dark = stored === "dark" || (stored !== "light" && window.matchMedia("(prefers-color-scheme: dark)").matches);
      if (dark) document.documentElement.classList.add("dark");
    } catch (e) {}
  })();
`;

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="fa" dir="rtl" className="h-full antialiased">
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
      </head>
      <body className="min-h-full flex flex-col font-sans">
        <ThemeProvider>
          <AuthProvider>{children}</AuthProvider>
          <Toaster />
        </ThemeProvider>
      </body>
    </html>
  );
}
