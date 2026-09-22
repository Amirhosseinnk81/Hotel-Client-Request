import { beforeEach, describe, expect, it, vi } from "vitest";

import type { Ticket } from "@/lib/api/types";

import {
  cacheWrite,
  clearOfflineData,
  enqueue,
  findCachedTicket,
  flushQueue,
  getQueue,
  readThrough,
  type FlushExecutors,
} from "./offline";

const ticket = (overrides: Partial<Ticket> = {}): Ticket =>
  ({ id: 7, title: "Extra towels", status: "IN_PROGRESS", updated_at: "t1", ...overrides }) as Ticket;

const networkDown = () => Promise.reject(new TypeError("Failed to fetch"));

function executors(overrides: Partial<FlushExecutors> = {}): FlushExecutors {
  return {
    getTicket: vi.fn(async (id: number) => ticket({ id })),
    updateTicket: vi.fn(async (id: number) => ticket({ id, updated_at: "t2" })),
    addNote: vi.fn(async () => ({})),
    ...overrides,
  };
}

const queueStatus = (userId = 1, baseUpdatedAt = "t1", ticketId = 7) =>
  enqueue(userId, {
    kind: "status",
    ticketId,
    ticketTitle: "Extra towels",
    payload: { status: "RESOLVED", resolution: "Delivered." },
    baseUpdatedAt,
  });

beforeEach(() => {
  window.localStorage.clear();
  window.sessionStorage.clear();
});

describe("readThrough", () => {
  it("remembers a good answer and serves it when the network is down", async () => {
    await readThrough("operator/tickets/7", async () => ticket());
    const offline = await readThrough<Ticket>("operator/tickets/7", networkDown);

    expect(offline.title).toBe("Extra towels");
  });

  it("passes server errors through instead of hiding them behind the cache", async () => {
    cacheWrite("operator/tickets/7", ticket());
    const forbidden = new Error("403");

    await expect(readThrough("operator/tickets/7", () => Promise.reject(forbidden))).rejects.toBe(forbidden);
  });

  it("still fails offline when nothing was cached", async () => {
    await expect(readThrough("operator/tickets/99", networkDown)).rejects.toBeInstanceOf(TypeError);
  });
});

describe("findCachedTicket", () => {
  it("finds a ticket in a cached list when its detail was never opened", () => {
    cacheWrite("operator/tickets?status=OPEN", [ticket({ id: 3 }), ticket({ id: 7, title: "Iron" })]);

    expect(findCachedTicket(7)?.title).toBe("Iron");
    expect(findCachedTicket(8)).toBeNull();
  });
});

describe("queue", () => {
  it("is kept per user", () => {
    queueStatus(1);

    expect(getQueue(1)).toHaveLength(1);
    expect(getQueue(2)).toHaveLength(0);
  });
});

describe("flushQueue", () => {
  it("sends status changes and notes in order", async () => {
    queueStatus();
    enqueue(1, { kind: "note", ticketId: 7, ticketTitle: "Extra towels", text: "Left at door" });
    const exec = executors();

    const report = await flushQueue(1, exec);

    expect(report.sent).toHaveLength(2);
    expect(exec.updateTicket).toHaveBeenCalledWith(7, { status: "RESOLVED", resolution: "Delivered." });
    expect(exec.addNote).toHaveBeenCalledWith(7, "Left at door");
    expect(getQueue(1)).toHaveLength(0);
  });

  it("drops a status change when the ticket changed meanwhile, instead of overwriting it", async () => {
    queueStatus(1, "t1");
    const exec = executors({ getTicket: vi.fn(async () => ticket({ updated_at: "someone-else" })) });

    const report = await flushQueue(1, exec);

    expect(report.conflicts).toHaveLength(1);
    expect(exec.updateTicket).not.toHaveBeenCalled();
    expect(getQueue(1)).toHaveLength(0);
  });

  it("doesn't mistake its own earlier replay for someone else's edit", async () => {
    // Two queued changes to one ticket, both made against the same copy.
    queueStatus(1, "t1");
    enqueue(1, {
      kind: "status",
      ticketId: 7,
      ticketTitle: "Extra towels",
      payload: { status: "OPEN" },
      baseUpdatedAt: "t1",
    });
    let current = ticket({ updated_at: "t1" });
    const exec = executors({
      getTicket: vi.fn(async () => current),
      updateTicket: vi.fn(async () => {
        current = ticket({ updated_at: current.updated_at + "+" });
        return current;
      }),
    });

    const report = await flushQueue(1, exec);

    expect(report.sent).toHaveLength(2);
    expect(report.conflicts).toHaveLength(0);
  });

  it("stops at the first network error and keeps the rest queued", async () => {
    queueStatus();
    enqueue(1, { kind: "note", ticketId: 7, ticketTitle: "Extra towels", text: "Later" });
    const exec = executors({ getTicket: vi.fn(networkDown) });

    const report = await flushQueue(1, exec);

    expect(report.sent).toHaveLength(0);
    expect(report.remaining).toBe(2);
    expect(getQueue(1)).toHaveLength(2);
  });

  it("drops what the server refuses, so it can't block the queue forever", async () => {
    queueStatus();
    const exec = executors({
      updateTicket: vi.fn(async () => {
        throw new Error("Invalid status transition");
      }),
    });

    const report = await flushQueue(1, exec);

    expect(report.rejected[0].message).toBe("Invalid status transition");
    expect(getQueue(1)).toHaveLength(0);
  });
});

describe("clearOfflineData", () => {
  it("wipes cached tickets and queued actions on logout, and nothing else", () => {
    cacheWrite("operator/tickets/7", ticket());
    queueStatus();
    window.localStorage.setItem("theme", "dark");

    clearOfflineData();

    expect(findCachedTicket(7)).toBeNull();
    expect(getQueue(1)).toHaveLength(0);
    expect(window.localStorage.getItem("theme")).toBe("dark");
  });
});
