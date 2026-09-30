/**
 * Windows desktop alerts for the operator panel.
 *
 * The browser's own Notification API — nothing installed, no native
 * helper. On Windows a notification from an open Chrome or Edge tab
 * lands in the action centre and pops a toast, which is exactly what was
 * asked for: the operator does not have to be looking at the panel.
 *
 * Three things this has to be honest about, because all three bite on a
 * hotel LAN and a silent failure looks like a broken feature:
 *
 *  1. It needs a **secure context** — https, or localhost. The panel
 *     served over plain http from a machine on the hotel network has no
 *     `Notification` at all, so `support()` says why and the settings
 *     row explains it instead of offering a dead switch.
 *  2. Permission must be asked for **from a click**. Browsers ignore (or
 *     in Chrome's case, permanently deny) a prompt that appears on page
 *     load, so nothing here asks on its own.
 *  3. "granted" is not forever. The user can revoke it in the browser,
 *     so every notification re-checks rather than trusting a flag.
 *
 * The sound stays with lib/chime.ts: a desktop alert is silent by
 * choice, so an operator watching the panel isn't told twice.
 */

const PREFERENCE_KEY = "operator-desktop-notifications";

export type NotifySupport =
  | { ok: true }
  | { ok: false; reason: "unsupported" | "insecure" | "denied" };

/**
 * Whether a desktop alert can be shown at all, and if not, which of the
 * three reasons it is — the panel shows the reason rather than a switch
 * that does nothing.
 */
export function support(): NotifySupport {
  if (typeof window === "undefined") return { ok: false, reason: "unsupported" };
  // `isSecureContext` is false for http on anything but localhost, which
  // is also when Notification is usually missing entirely.
  if (!window.isSecureContext) return { ok: false, reason: "insecure" };
  // Truthiness, not `"Notification" in window`: the property can exist
  // and be undefined (older WebViews, and some embedded browsers).
  if (!window.Notification) return { ok: false, reason: "unsupported" };
  if (Notification.permission === "denied") return { ok: false, reason: "denied" };
  return { ok: true };
}

/** Has the browser already been asked, and said yes? */
export function isGranted(): boolean {
  return support().ok && Notification.permission === "granted";
}

/** The operator's own switch, per browser. Off until they turn it on. */
export function isEnabled(): boolean {
  if (typeof window === "undefined") return false;
  try {
    return window.localStorage.getItem(PREFERENCE_KEY) === "on";
  } catch {
    // Private windows and blocked site data both land here.
    return false;
  }
}

export function setEnabled(enabled: boolean): void {
  try {
    window.localStorage.setItem(PREFERENCE_KEY, enabled ? "on" : "off");
  } catch {
    // Not being able to remember the choice is not worth an error.
  }
}

/**
 * Ask the browser for permission. Must be called from a real click —
 * see the note at the top of this file.
 */
export async function requestPermission(): Promise<boolean> {
  if (!support().ok) return false;
  if (Notification.permission === "granted") return true;
  try {
    return (await Notification.requestPermission()) === "granted";
  } catch {
    return false;
  }
}

/**
 * Show one alert, if the operator turned them on and the browser still
 * allows it. Never throws — a notification that can't be shown must not
 * take down whatever was handling the event.
 *
 * `tag` replaces an earlier alert with the same tag instead of stacking,
 * so twenty new tickets don't bury the desktop.
 */
export function notify(title: string, body: string, tag?: string): void {
  if (!isEnabled() || !isGranted()) return;
  try {
    const notification = new Notification(title, {
      body,
      tag,
      lang: "fa",
      dir: "rtl",
      // Silent on purpose: lib/chime.ts already makes the sound, and two
      // at once is worse than either.
      silent: true,
    });
    notification.onclick = () => {
      window.focus();
      notification.close();
    };
  } catch {
    // Some browsers refuse `new Notification` outside a service worker.
  }
}
