import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { FormError } from "./form-error";

describe("FormError", () => {
  it("renders nothing when message is null", () => {
    const { container } = render(<FormError message={null} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("renders the message text when provided", () => {
    render(<FormError message="نام کاربری اشتباه است" />);
    expect(screen.getByText("نام کاربری اشتباه است")).toBeInTheDocument();
  });
});
