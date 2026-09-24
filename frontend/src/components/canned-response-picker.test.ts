import { describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api/client", () => ({ getCannedResponses: vi.fn(async () => []) }));

const { appendText } = await import("./canned-response-picker");

describe("appendText", () => {
  it("uses the ready-made text alone when the field is empty", () => {
    expect(appendText("", "Towels delivered.")).toBe("Towels delivered.");
    expect(appendText("   ", "Towels delivered.")).toBe("Towels delivered.");
  });

  it("adds it on a new line after what the operator already wrote", () => {
    expect(appendText("Two towels\n", "Delivered to the room.")).toBe("Two towels\nDelivered to the room.");
  });
});
