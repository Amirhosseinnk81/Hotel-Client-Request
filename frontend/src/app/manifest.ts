import type { MetadataRoute } from "next";

/**
 * Lets the operator panel be installed as an app (operator offline mode).
 * Colours are the Araz palette tokens from globals.css.
 */
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "پنل اپراتور — درخواست‌های مهمان هتل",
    short_name: "پنل اپراتور",
    description: "سامانه مدیریت درخواست‌های مهمانان هتل",
    start_url: "/operator",
    scope: "/",
    display: "standalone",
    dir: "rtl",
    lang: "fa",
    background_color: "#ffffff",
    theme_color: "#7c5f47",
    icons: [{ src: "/icon.svg", sizes: "any", type: "image/svg+xml", purpose: "any" }],
  };
}
