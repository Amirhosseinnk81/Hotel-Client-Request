import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ITRequestTemplate, OutgoingITRequest } from "@/lib/api/types";

const getRequestsMock = vi.fn();
const getTemplatesMock = vi.fn();
const createRequestMock = vi.fn();
const addAttachmentMock = vi.fn();
const rateMock = vi.fn();
const toastMock = vi.fn();

// Only the network is stubbed; ApiError stays real, because
// `instanceof ApiError` is what picks the server's message over the
// generic fallback.
vi.mock("@/lib/api/client", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api/client")>()),
  getOutgoingItRequests: (...a: unknown[]) => getRequestsMock(...a),
  getItRequestTemplates: (...a: unknown[]) => getTemplatesMock(...a),
  createOutgoingItRequest: (...a: unknown[]) => createRequestMock(...a),
  addItRequestAttachment: (...a: unknown[]) => addAttachmentMock(...a),
  rateItRequest: (...a: unknown[]) => rateMock(...a),
}));

vi.mock("@/hooks/use-toast", () => ({
  toast: (...a: unknown[]) => toastMock(...a),
}));

const ITRequestsPage = (await import("./page")).default;
const { ApiError } = await import("@/lib/api/client");

function template(overrides: Partial<ITRequestTemplate> = {}): ITRequestTemplate {
  return {
    id: 1,
    title: "پرینتر کار نمی‌کند",
    description: "روشن است ولی چاپ نمی‌کند.",
    icon: "Printer",
    priority: "HIGH",
    order: 0,
    ...overrides,
  };
}

function request(overrides: Partial<OutgoingITRequest> = {}): OutgoingITRequest {
  return {
    id: 7,
    title: "پرینتر پذیرش",
    description: "",
    priority: "HIGH",
    status: "PENDING",
    requesting_department_name: "پذیرش",
    requested_by_username: "fd_op",
    assigned_to_username: null,
    attachments: [],
    rating: null,
    feedback: "",
    rated_at: null,
    can_be_rated: false,
    resolved_at: null,
    created_at: "2026-09-24T09:00:00Z",
    updated_at: "2026-09-24T09:00:00Z",
    ...overrides,
  };
}

describe("ITRequestsPage", () => {
  beforeEach(() => {
    getRequestsMock.mockReset().mockResolvedValue([request()]);
    getTemplatesMock.mockReset().mockResolvedValue([template()]);
    createRequestMock.mockReset().mockResolvedValue(request({ id: 9, title: "نو" }));
    addAttachmentMock.mockReset().mockResolvedValue({ id: 1 });
    rateMock.mockReset().mockResolvedValue(request({ rating: 5 }));
    toastMock.mockReset();
  });

  it("fills the form from a one-click template", async () => {
    render(<ITRequestsPage />);

    await userEvent.click(await screen.findByRole("button", { name: /پرینتر کار نمی‌کند/ }));

    expect(screen.getByLabelText(/موضوع/)).toHaveValue("پرینتر کار نمی‌کند");
    expect(screen.getByLabelText("توضیح")).toHaveValue("روشن است ولی چاپ نمی‌کند.");
  });

  it("leaves the filled fields editable", async () => {
    render(<ITRequestsPage />);
    await userEvent.click(await screen.findByRole("button", { name: /پرینتر کار نمی‌کند/ }));

    const title = screen.getByLabelText(/موضوع/);
    await userEvent.clear(title);
    await userEvent.type(title, "چیز دیگری");

    expect(title).toHaveValue("چیز دیگری");
  });

  it("hides the shortcuts when the hotel has defined none", async () => {
    getTemplatesMock.mockResolvedValue([]);

    render(<ITRequestsPage />);
    await screen.findByText("پرینتر پذیرش");

    expect(screen.queryByText("درخواست‌های رایج")).not.toBeInTheDocument();
  });

  it("sends the photo after the request it belongs to", async () => {
    render(<ITRequestsPage />);
    await userEvent.click(await screen.findByRole("button", { name: /پرینتر کار نمی‌کند/ }));
    const file = new File(["x"], "printer.png", { type: "image/png" });
    await userEvent.upload(screen.getByLabelText(/عکس مشکل/), file);

    await userEvent.click(screen.getByRole("button", { name: /ارسال به IT/ }));

    await waitFor(() => expect(addAttachmentMock).toHaveBeenCalled());
    // The id of the request that was just created, not a guess.
    expect(addAttachmentMock).toHaveBeenCalledWith(9, file);
  });

  it("keeps the request when only the photo fails", async () => {
    addAttachmentMock.mockRejectedValue(new ApiError(400, "فایل خیلی بزرگ است."));

    render(<ITRequestsPage />);
    await userEvent.click(await screen.findByRole("button", { name: /پرینتر کار نمی‌کند/ }));
    await userEvent.upload(
      screen.getByLabelText(/عکس مشکل/),
      new File(["x"], "big.png", { type: "image/png" })
    );
    await userEvent.click(screen.getByRole("button", { name: /ارسال به IT/ }));

    await waitFor(() =>
      expect(toastMock).toHaveBeenCalledWith(
        expect.objectContaining({ description: "فایل خیلی بزرگ است." })
      )
    );
    // …and the request itself is still reported as sent.
    expect(toastMock).toHaveBeenCalledWith(
      expect.objectContaining({ title: "درخواست به IT رفت" })
    );
  });

  it("shows an attached photo on the request", async () => {
    getRequestsMock.mockResolvedValue([
      request({
        attachments: [
          {
            id: 3,
            image: "http://localhost:8000/media/it_request_attachments/7/printer.png",
            uploaded_by_username: "fd_op",
            created_at: "2026-09-24T09:05:00Z",
          },
        ],
      }),
    ]);

    render(<ITRequestsPage />);

    const image = await screen.findByAltText("عکس پیوست درخواست");
    expect(image).toHaveAttribute("src", expect.stringContaining("printer.png"));
  });

  it("offers the feedback box only once IT has finished", async () => {
    render(<ITRequestsPage />);
    await screen.findByText("پرینتر پذیرش");
    expect(screen.queryByRole("button", { name: "ثبت بازخورد" })).not.toBeInTheDocument();

    getRequestsMock.mockResolvedValue([request({ status: "COMPLETED", can_be_rated: true })]);
    render(<ITRequestsPage />);

    expect(await screen.findByRole("button", { name: "ثبت بازخورد" })).toBeInTheDocument();
  });

  it("sends the score and the comment", async () => {
    getRequestsMock.mockResolvedValue([request({ status: "COMPLETED", can_be_rated: true })]);

    render(<ITRequestsPage />);
    await userEvent.click(await screen.findByRole("button", { name: "ثبت بازخورد" }));
    // The fourth star; matched by position so the test doesn't depend on
    // whether the label renders its number in Latin or Persian digits.
    await userEvent.click(screen.getAllByRole("button", { name: /ستاره/ })[3]);
    await userEvent.type(screen.getByPlaceholderText(/توضیح اختیاری/), "ممنون");
    await userEvent.click(screen.getByRole("button", { name: /ثبت بازخورد/ }));

    await waitFor(() => expect(rateMock).toHaveBeenCalledWith(7, 4, "ممنون"));
  });

  it("will not send a rating with no stars chosen", async () => {
    getRequestsMock.mockResolvedValue([request({ status: "COMPLETED", can_be_rated: true })]);

    render(<ITRequestsPage />);
    await userEvent.click(await screen.findByRole("button", { name: "ثبت بازخورد" }));
    await userEvent.click(screen.getByRole("button", { name: /ثبت بازخورد/ }));

    expect(rateMock).not.toHaveBeenCalled();
  });

  it("shows the feedback already given instead of the box", async () => {
    getRequestsMock.mockResolvedValue([
      request({ status: "COMPLETED", rating: 5, feedback: "سریع بود", can_be_rated: false }),
    ]);

    render(<ITRequestsPage />);

    expect(await screen.findByText("«سریع بود»")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "ثبت بازخورد" })).not.toBeInTheDocument();
  });
});
