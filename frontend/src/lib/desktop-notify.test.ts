import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { isEnabled, isGranted, notify, setEnabled, support } from "./desktop-notify";

/**
 * The point of these tests is the three ways a desktop alert quietly
 * fails on a hotel network — no API, not a secure context, permission
 * denied — because each one has to show the operator a reason instead of
 * a switch that does nothing.
 */

class FakeNotification {
  static permission: NotificationPermission = "granted";
  static requestPermission = vi.fn(async () => FakeNotification.permission);
  static shown: Array<{ title: string; options?: NotificationOptions }> = [];
  onclick: (() => void) | null = null;
  constructor(title: string, options?: NotificationOptions) {
    FakeNotification.shown.push({ title, options });
  }
  close() {}
}

function secureWith(permission: NotificationPermission) {
  FakeNotification.permission = permission;
  vi.stubGlobal("isSecureContext", true);
  vi.stubGlobal("Notification", FakeNotification);
}

beforeEach(() => {
  FakeNotification.shown = [];
  window.localStorage.clear();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("support", () => {
  it("names plain http as the reason, not a missing feature", () => {
    // The panel served over http from a machine on the hotel LAN: the
    // answer has to be "needs HTTPS", because that is what the operator
    // (or whoever deploys it) can act on.
    vi.stubGlobal("isSecureContext", false);
    expect(support()).toEqual({ ok: false, reason: "insecure" });
  });

  it("reports a browser with no Notification API", () => {
    vi.stubGlobal("isSecureContext", true);
    vi.stubGlobal("Notification", undefined);
    expect(support()).toEqual({ ok: false, reason: "unsupported" });
  });

  it("reports a permission the user already refused", () => {
    secureWith("denied");
    expect(support()).toEqual({ ok: false, reason: "denied" });
  });

  it("is happy on https with permission granted", () => {
    secureWith("granted");
    expect(support()).toEqual({ ok: true });
    expect(isGranted()).toBe(true);
  });
});

describe("the operator's own switch", () => {
  it("starts off — nothing pops up until they ask for it", () => {
    expect(isEnabled()).toBe(false);
  });

  it("remembers the choice per browser", () => {
    setEnabled(true);
    expect(isEnabled()).toBe(true);
    setEnabled(false);
    expect(isEnabled()).toBe(false);
  });
});

describe("notify", () => {
  it("shows nothing while the switch is off, even with permission", () => {
    secureWith("granted");
    notify("درخواست جدید", "اتاق ۳۰۵");
    expect(FakeNotification.shown).toEqual([]);
  });

  it("shows a silent, tagged alert once the switch is on", () => {
    secureWith("granted");
    setEnabled(true);

    notify("درخواست جدید", "اتاق ۳۰۵", "ticket-1");

    expect(FakeNotification.shown).toHaveLength(1);
    const { title, options } = FakeNotification.shown[0];
    expect(title).toBe("درخواست جدید");
    // Silent because lib/chime.ts already makes the sound; tagged so
    // twenty new tickets replace each other instead of stacking.
    expect(options?.silent).toBe(true);
    expect(options?.tag).toBe("ticket-1");
  });

  it("shows nothing when permission was revoked after the switch was set", () => {
    secureWith("denied");
    setEnabled(true);
    notify("درخواست جدید", "اتاق ۳۰۵");
    expect(FakeNotification.shown).toEqual([]);
  });

  it("never throws when the browser refuses to construct one", () => {
    vi.stubGlobal("isSecureContext", true);
    vi.stubGlobal(
      "Notification",
      class {
        static permission: NotificationPermission = "granted";
        constructor() {
          throw new Error("only allowed from a service worker");
        }
      }
    );
    setEnabled(true);
    expect(() => notify("x", "y")).not.toThrow();
  });
});
