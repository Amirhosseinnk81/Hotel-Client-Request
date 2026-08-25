import type { Metadata } from "next";
import "@fontsource-variable/vazirmatn";
import "./globals.css";

import { AuthProvider } from "@/contexts/auth-context";
import { Toaster } from "@/components/toaster";

export const metadata: Metadata = {
  title: "پلتفرم درخواست‌های مهمان هتل",
  description: "سامانه مدیریت درخواست‌های مهمانان هتل",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="fa" dir="rtl" className="h-full antialiased">
      <body className="min-h-full flex flex-col font-sans">
        <AuthProvider>{children}</AuthProvider>
        <Toaster />
      </body>
    </html>
  );
}
