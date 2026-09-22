import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api/client", () => ({
  API_URL: "http://api.test/api/v1",
  getFreshAccessToken: vi.fn(async () => "token-1"),
}));

const { parseEventStream, reconnectDelay, runOperatorEventStream } = await import("./realtime");
const { getFreshAccessToken } = await import("@/lib/api/client");

const cursor = { ticket: 5, history: 9 };
const block = (event: string, data: object) => `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`;

describe("parseEventStream", () => {
  it("parses complete events and keeps the incomplete tail", () => {
    const text =
      "retry: 3000\n\n" +
      block("ticket.created", { id: 1, title: "Towels", cursor }) +
      "event: heartbeat\ndata: {\"active_tickets\"";

    const { events, rest } = parseEventStream(text);

    expect(events).toEqual([{ type: "ticket.created", id: 1, title: "Towels", cursor }]);
    expect(rest).toBe('event: heartbeat\ndata: {"active_tickets"');
  });

  it("joins an event split across two network chunks", () => {
    const full = block("ticket.assigned", { id: 3, title: "Iron", by: null, cursor });
    const first = parseEventStream(full.slice(0, 20));
    const second = parseEventStream(first.rest + full.slice(20));

    expect(first.events).toHaveLength(0);
    expect(second.events[0]).toMatchObject({ type: "ticket.assigned", id: 3 });
  });

  it("skips a garbled event instead of throwing", () => {
    const { events } = parseEventStream("event: heartbeat\ndata: {nope\n\n" + block("reconnect", { cursor }));

    expect(events).toEqual([{ type: "reconnect", cursor }]);
  });

  it("accepts CRLF line endings", () => {
    const { events } = parseEventStream(block("reconnect", { cursor }).replace(/\n/g, "\r\n"));

    expect(events).toHaveLength(1);
  });
});

describe("reconnectDelay", () => {
  it("backs off and caps at 30 seconds", () => {
    expect(reconnectDelay(1)).toBe(2000);
    expect(reconnectDelay(2)).toBe(4000);
    expect(reconnectDelay(10)).toBe(30_000);
  });
});

describe("runOperatorEventStream", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  function streamOf(text: string): Response {
    const body = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(new TextEncoder().encode(text));
        controller.close();
      },
    });
    return new Response(body, { status: 200, headers: { "Content-Type": "text/event-stream" } });
  }

  it("sends the token as a header, delivers events and resumes from the last cursor", async () => {
    const controller = new AbortController();
    const urls: string[] = [];
    const headers: Headers[] = [];
    const fetchMock = vi.fn(async (url: string, init: RequestInit) => {
      urls.push(url);
      headers.push(new Headers(init.headers));
      if (urls.length === 1) return streamOf(block("ticket.created", { id: 1, title: "Towels", cursor }));
      controller.abort();
      throw new DOMException("aborted", "AbortError");
    });
    vi.stubGlobal("fetch", fetchMock);
    const received: string[] = [];

    await runOperatorEventStream((event) => received.push(event.type), controller.signal);

    expect(received).toEqual(["ticket.created"]);
    expect(headers[0].get("Authorization")).toBe("Bearer token-1");
    expect(urls[0]).toBe("http://api.test/api/v1/operator/events/");
    // The token never goes in the URL; the cursor does, on reconnect.
    expect(urls[1]).toBe("http://api.test/api/v1/operator/events/?after_ticket=5&after_history=9");
  });

  it("stops for good when the caller isn't an operator (403)", async () => {
    const fetchMock = vi.fn(async () => new Response("{}", { status: 403 }));
    vi.stubGlobal("fetch", fetchMock);

    await runOperatorEventStream(() => {}, new AbortController().signal);

    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("gives up when the session is gone", async () => {
    vi.useFakeTimers();
    vi.mocked(getFreshAccessToken).mockResolvedValue(null);
    vi.stubGlobal("fetch", vi.fn());

    const done = runOperatorEventStream(() => {}, new AbortController().signal);
    await vi.runAllTimersAsync();
    await done;

    expect(fetch).not.toHaveBeenCalled();
    vi.useRealTimers();
    vi.mocked(getFreshAccessToken).mockResolvedValue("token-1");
  });
});
