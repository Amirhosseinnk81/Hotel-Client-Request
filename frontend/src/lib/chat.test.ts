import { beforeEach, describe, expect, it, vi } from "vitest";

const getChatConfig = vi.fn();
const getChatSocketTicket = vi.fn();

vi.mock("@/lib/api/client", () => ({
  API_URL: "https://hotel.test/api/v1",
  getChatConfig,
  getChatSocketTicket,
}));

const { chatConfig, openChatSocket, resetChatConfigCache, socketUrl } = await import("./chat");

beforeEach(() => {
  resetChatConfigCache();
  getChatConfig.mockReset();
  getChatSocketTicket.mockReset();
});

describe("socketUrl", () => {
  it("derives the socket URL from the API URL, keeping the scheme", () => {
    expect(socketUrl(12, "abc")).toBe("wss://hotel.test/ws/chat/12/?ticket=abc");
  });

  it("escapes the ticket instead of pasting it in raw", () => {
    expect(socketUrl(1, "a b/c")).toContain("ticket=a%20b%2Fc");
  });
});

describe("chatConfig", () => {
  it("asks the server once and remembers the answer", async () => {
    getChatConfig.mockResolvedValue({
      transport: "websocket",
      websocket_path: "/ws/chat/",
      poll_seconds: 3,
    });

    expect((await chatConfig()).transport).toBe("websocket");
    expect((await chatConfig()).transport).toBe("websocket");
    expect(getChatConfig).toHaveBeenCalledTimes(1);
  });

  it("falls back to the transport that needs no extra infrastructure", async () => {
    // If we can't ask, assume SSE: it works on the hotel's current WSGI
    // server, while assuming WebSockets would mean opening sockets that
    // nothing is listening on.
    getChatConfig.mockRejectedValue(new Error("offline"));
    expect((await chatConfig()).transport).toBe("sse");
  });
});

describe("openChatSocket", () => {
  it("opens nothing on the SSE transport", async () => {
    getChatConfig.mockResolvedValue({ transport: "sse", websocket_path: "", poll_seconds: 3 });

    const connection = await openChatSocket(7, new AbortController().signal);

    expect(connection).toBeNull();
    // No ticket is spent either — there is no handshake to authenticate.
    expect(getChatSocketTicket).not.toHaveBeenCalled();
  });

  it("spends a single-use ticket per attempt, never the access token", async () => {
    getChatConfig.mockResolvedValue({
      transport: "websocket",
      websocket_path: "/ws/chat/",
      poll_seconds: 3,
    });
    getChatSocketTicket.mockResolvedValue({ ticket: "one-shot", expires_in: 30 });

    const opened: string[] = [];
    class FakeSocket {
      static OPEN = 1;
      readyState = 1;
      onopen: (() => void) | null = null;
      onmessage: ((event: { data: string }) => void) | null = null;
      onclose: (() => void) | null = null;
      sent: string[] = [];
      constructor(url: string) {
        opened.push(url);
      }
      send(data: string) {
        this.sent.push(data);
      }
      close() {}
    }
    vi.stubGlobal("WebSocket", FakeSocket);

    const controller = new AbortController();
    const connection = await openChatSocket(7, controller.signal);

    expect(getChatSocketTicket).toHaveBeenCalledTimes(1);
    expect(opened).toEqual(["wss://hotel.test/ws/chat/7/?ticket=one-shot"]);
    expect(connection?.send("سلام")).toBe(true);

    controller.abort();
    vi.unstubAllGlobals();
  });
});
