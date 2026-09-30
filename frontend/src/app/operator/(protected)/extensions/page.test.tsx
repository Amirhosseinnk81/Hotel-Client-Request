import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { Extension } from "@/lib/api/types";

const getExtensionsMock = vi.fn();
const exportExtensionsMock = vi.fn();
const getDepartmentsMock = vi.fn();
const getVersionMock = vi.fn();
const downloadMock = vi.fn();
const toastMock = vi.fn();
const writeTextMock = vi.fn();

// Only the network and the browser download are stubbed; ApiError stays
// the real class, because `instanceof ApiError` is what decides between
// the server's own message and the generic fallback.
vi.mock("@/lib/api/client", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api/client")>()),
  getExtensions: (...args: unknown[]) => getExtensionsMock(...args),
  exportExtensions: (...args: unknown[]) => exportExtensionsMock(...args),
  getDepartments: (...args: unknown[]) => getDepartmentsMock(...args),
  getExtensionsVersion: (...args: unknown[]) => getVersionMock(...args),
}));

vi.mock("@/lib/utils", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/utils")>()),
  downloadBlob: (...args: unknown[]) => downloadMock(...args),
}));

vi.mock("@/hooks/use-toast", () => ({
  toast: (...args: unknown[]) => toastMock(...args),
}));

const ExtensionsPage = (await import("./page")).default;
const { ApiError } = await import("@/lib/api/client");

function row(overrides: Partial<Extension> = {}): Extension {
  return {
    id: 1,
    extension: "100",
    title: "پذیرش",
    person_name: "رضا مرادی",
    department: 3,
    department_name: "پذیرش",
    department_working_hours: "۲۴ ساعته",
    location: "لابی",
    email: "",
    mobile: "",
    notes: "",
    is_active: true,
    created_at: "2026-09-01T10:00:00Z",
    updated_at: "2026-09-01T10:00:00Z",
    ...overrides,
  };
}

describe("ExtensionsPage", () => {
  beforeEach(() => {
    getExtensionsMock.mockReset().mockResolvedValue([row()]);
    exportExtensionsMock.mockReset().mockResolvedValue(new Blob(["%PDF-1.4"]));
    getDepartmentsMock.mockReset().mockResolvedValue([]);
    getVersionMock.mockReset().mockResolvedValue("1:1:x");
    downloadMock.mockReset();
    toastMock.mockReset();
    writeTextMock.mockReset().mockResolvedValue(undefined);
    Object.assign(navigator, { clipboard: { writeText: writeTextMock } });
    window.localStorage.clear();
  });

  it("shows a number with its department's working hours", async () => {
    render(<ExtensionsPage />);

    // "پذیرش" is both the title and the department here, so assert on
    // the unambiguous cells instead.
    expect(await screen.findByText("رضا مرادی")).toBeInTheDocument();
    expect(screen.getByText("۲۴ ساعته")).toBeInTheDocument();
    expect(screen.getByText("لابی")).toBeInTheDocument();
    // The number itself is shown in Persian digits.
    expect(screen.getByText("۱۰۰")).toBeInTheDocument();
  });

  it("marks a number that is out of use", async () => {
    getExtensionsMock.mockResolvedValue([row({ is_active: false })]);

    render(<ExtensionsPage />);

    expect(await screen.findByText("غیرفعال")).toBeInTheDocument();
  });

  it("says so when nothing matches instead of showing an empty table", async () => {
    getExtensionsMock.mockResolvedValue([]);

    render(<ExtensionsPage />);

    expect(await screen.findByText(/پیدا نشد/)).toBeInTheDocument();
  });

  it("downloads an export with the same filters as the list", async () => {
    render(<ExtensionsPage />);
    await screen.findByText("۱۰۰");

    await userEvent.click(screen.getByRole("button", { name: /PDF/ }));

    await waitFor(() => expect(exportExtensionsMock).toHaveBeenCalled());
    const [kind, params] = exportExtensionsMock.mock.calls[0];
    expect(kind).toBe("pdf");
    // The same object the list was fetched with — an export must never
    // disagree with what is on screen.
    expect(params).toEqual(getExtensionsMock.mock.calls.at(-1)?.[0]);
    expect(downloadMock).toHaveBeenCalledWith(expect.any(Blob), "extensions.pdf");
  });

  it("reports the server's reason when an export is refused", async () => {
    exportExtensionsMock.mockRejectedValue(new ApiError(403, "اجازه ندارید."));

    render(<ExtensionsPage />);
    await screen.findByText("۱۰۰");
    await userEvent.click(screen.getByRole("button", { name: /اکسل/ }));

    await waitFor(() =>
      expect(toastMock).toHaveBeenCalledWith(
        expect.objectContaining({ description: "اجازه ندارید.", variant: "destructive" })
      )
    );
  });

  it("shows why the list could not be loaded", async () => {
    getExtensionsMock.mockRejectedValue(new ApiError(500, "خطای سرور."));

    render(<ExtensionsPage />);

    expect(await screen.findByText("خطای سرور.")).toBeInTheDocument();
  });

  it("remembers a starred number and can show only those", async () => {
    getExtensionsMock.mockResolvedValue([row(), row({ id: 2, extension: "210", title: "لباسشویی" })]);

    const { unmount } = render(<ExtensionsPage />);
    await screen.findByText("۱۰۰");
    await userEvent.click(screen.getAllByRole("button", { name: "افزودن به علاقه‌مندی‌ها" })[0]);
    await userEvent.click(screen.getByRole("button", { name: /فقط علاقه‌مندی‌ها/ }));

    expect(screen.getByText("۱۰۰")).toBeInTheDocument();
    expect(screen.queryByText("۲۱۰")).not.toBeInTheDocument();

    // …and it survives coming back to the page.
    unmount();
    render(<ExtensionsPage />);
    await userEvent.click(await screen.findByRole("button", { name: /فقط علاقه‌مندی‌ها/ }));
    expect(screen.queryByText("۲۱۰")).not.toBeInTheDocument();
  });

  it("says so when nothing is starred yet", async () => {
    render(<ExtensionsPage />);
    await screen.findByText("۱۰۰");

    await userEvent.click(screen.getByRole("button", { name: /فقط علاقه‌مندی‌ها/ }));

    expect(screen.getByText(/هنوز داخلی‌ای را نشان نکرده‌اید/)).toBeInTheDocument();
  });

  it("copies the number itself, not the row", async () => {
    render(<ExtensionsPage />);
    await screen.findByText("۱۰۰");

    await userEvent.click(screen.getByRole("button", { name: "کپی داخلی 100" }));

    expect(writeTextMock).toHaveBeenCalledWith("100");
  });

  it("opens the details box on a row, without starring it", async () => {
    render(<ExtensionsPage />);
    await userEvent.click(await screen.findByText("رضا مرادی"));

    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByText("لابی")).toBeInTheDocument();
    expect(within(dialog).getByText("۲۴ ساعته")).toBeInTheDocument();
  });

  it("switches to cards and remembers it", async () => {
    const { unmount } = render(<ExtensionsPage />);
    await screen.findByText("۱۰۰");

    await userEvent.click(screen.getByRole("button", { name: "نمای کارت" }));
    expect(screen.queryByRole("table")).not.toBeInTheDocument();

    unmount();
    render(<ExtensionsPage />);
    await screen.findByText("۱۰۰");
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });

  it("re-reads the list only when the version marker moves", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    try {
      render(<ExtensionsPage />);
      await vi.advanceTimersByTimeAsync(300);
      const afterFirstLoad = getExtensionsMock.mock.calls.length;

      // Same marker twice: nothing to re-read.
      await vi.advanceTimersByTimeAsync(30_000);
      await vi.advanceTimersByTimeAsync(30_000);
      expect(getExtensionsMock.mock.calls.length).toBe(afterFirstLoad);

      // Someone else edited the directory.
      getVersionMock.mockResolvedValue("2:2:y");
      await vi.advanceTimersByTimeAsync(30_000);
      expect(getExtensionsMock.mock.calls.length).toBeGreaterThan(afterFirstLoad);
    } finally {
      vi.useRealTimers();
    }
  });
});
