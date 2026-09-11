import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const exportMock = vi.fn();
const downloadMock = vi.fn();
const toastMock = vi.fn();

// Only the network call and the browser download are stubbed. ApiError
// stays the real class, because the component's `instanceof ApiError`
// check is exactly what decides between showing the server's reason and
// the generic fallback — faking it would test nothing.
vi.mock("@/lib/api/client", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api/client")>()),
  exportTicketPdf: (...args: unknown[]) => exportMock(...args),
}));

// cn() has to stay real: Button builds its className with it.
vi.mock("@/lib/utils", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/utils")>()),
  downloadBlob: (...args: unknown[]) => downloadMock(...args),
}));

vi.mock("@/hooks/use-toast", () => ({
  toast: (...args: unknown[]) => toastMock(...args),
}));

// Imported after the mocks above, same as use-require-role.test.tsx.
const { TicketPdfExportButton } = await import("./ticket-pdf-export-button");
const { ApiError } = await import("@/lib/api/client");

const samplePdf = () => new Blob(["%PDF-1.4"], { type: "application/pdf" });

describe("TicketPdfExportButton", () => {
  beforeEach(() => {
    exportMock.mockReset();
    downloadMock.mockReset();
    toastMock.mockReset();
  });

  it("downloads the ticket's PDF under a ticket-numbered filename", async () => {
    const pdf = samplePdf();
    exportMock.mockResolvedValue(pdf);
    const user = userEvent.setup();

    render(<TicketPdfExportButton ticketId={124} />);
    await user.click(screen.getByRole("button", { name: "دریافت PDF" }));

    await waitFor(() => expect(downloadMock).toHaveBeenCalledWith(pdf, "ticket-124.pdf"));
    expect(exportMock).toHaveBeenCalledWith(124);
    expect(toastMock).not.toHaveBeenCalled();
  });

  it("disables itself while the export is in flight, so a double tap can't start two downloads", async () => {
    let finish!: (blob: Blob) => void;
    exportMock.mockImplementation(
      () =>
        new Promise<Blob>((resolve) => {
          finish = resolve;
        }),
    );
    const user = userEvent.setup();

    render(<TicketPdfExportButton ticketId={124} />);
    const button = screen.getByRole("button", { name: "دریافت PDF" });

    await user.click(button);
    expect(button).toBeDisabled();

    // A second tap on a slow hotel connection must not queue another export.
    await user.click(button);
    expect(exportMock).toHaveBeenCalledTimes(1);

    finish(samplePdf());
    await waitFor(() => expect(button).toBeEnabled());
  });

  it("shows the server's reason when the export is refused", async () => {
    exportMock.mockRejectedValue(new ApiError(404, "درخواست مورد نظر یافت نشد."));
    const user = userEvent.setup();

    render(<TicketPdfExportButton ticketId={124} />);
    const button = screen.getByRole("button", { name: "دریافت PDF" });
    await user.click(button);

    await waitFor(() =>
      expect(toastMock).toHaveBeenCalledWith({
        variant: "destructive",
        title: "دریافت PDF ناموفق بود",
        description: "درخواست مورد نظر یافت نشد.",
      }),
    );
    expect(downloadMock).not.toHaveBeenCalled();
    // ...and it stays usable, so the guest can simply try again.
    await waitFor(() => expect(button).toBeEnabled());
  });

  it("falls back to a generic message when the failure isn't an API error", async () => {
    // e.g. the wifi dropping mid-request: fetch rejects with a TypeError
    // whose message means nothing to a guest.
    exportMock.mockRejectedValue(new TypeError("Failed to fetch"));
    const user = userEvent.setup();

    render(<TicketPdfExportButton ticketId={124} />);
    await user.click(screen.getByRole("button", { name: "دریافت PDF" }));

    await waitFor(() =>
      expect(toastMock).toHaveBeenCalledWith(
        expect.objectContaining({
          variant: "destructive",
          description: "لطفاً دوباره تلاش کنید.",
        }),
      ),
    );
    expect(downloadMock).not.toHaveBeenCalled();
  });
});
