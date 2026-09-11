import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ThemeProvider } from "@/contexts/theme-context";

import { ThemeToggle } from "./theme-toggle";

// Rendered inside the real ThemeProvider rather than a mocked useTheme:
// unlike AuthProvider, it has no network dependency, and the behaviour
// worth pinning is the round trip between the button, the <html> class,
// and the "theme" localStorage key. That key is a contract, not an
// implementation detail: the inline script in app/layout.tsx reads it
// back before hydration on the next load, so renaming it on one side
// only would silently reset every guest to light mode.
function renderToggle() {
  return render(
    <ThemeProvider>
      <ThemeToggle />
    </ThemeProvider>,
  );
}

function resetTheme() {
  document.documentElement.classList.remove("dark");
  window.localStorage.clear();
}

describe("ThemeToggle", () => {
  beforeEach(resetTheme);
  afterEach(resetTheme);

  it("offers dark mode when the page is in light mode", () => {
    renderToggle();

    expect(screen.getByRole("button", { name: "تغییر به حالت تاریک" })).toBeInTheDocument();
  });

  it("reflects a dark theme that was applied before React mounted", () => {
    // The inline script in app/layout.tsx sets this class before
    // hydration, so the toggle has to read the DOM rather than assume
    // light — otherwise its label would be wrong on every dark reload.
    document.documentElement.classList.add("dark");

    renderToggle();

    expect(screen.getByRole("button", { name: "تغییر به حالت روشن" })).toBeInTheDocument();
  });

  it("switches to dark: sets the <html> class, persists the choice, and flips its label", async () => {
    const user = userEvent.setup();
    renderToggle();

    await user.click(screen.getByRole("button", { name: "تغییر به حالت تاریک" }));

    expect(document.documentElement).toHaveClass("dark");
    expect(window.localStorage.getItem("theme")).toBe("dark");
    expect(screen.getByRole("button", { name: "تغییر به حالت روشن" })).toBeInTheDocument();
  });

  it("switches back to light on a second click", async () => {
    const user = userEvent.setup();
    renderToggle();
    const button = screen.getByRole("button");

    await user.click(button);
    await user.click(button);

    expect(document.documentElement).not.toHaveClass("dark");
    expect(window.localStorage.getItem("theme")).toBe("light");
    expect(screen.getByRole("button", { name: "تغییر به حالت تاریک" })).toBeInTheDocument();
  });

  it("fails loudly when rendered outside ThemeProvider", () => {
    // Without this guard, a header that forgot the provider would render
    // a button that silently does nothing when clicked.
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => {});

    expect(() => render(<ThemeToggle />)).toThrow(
      "useTheme must be used within a ThemeProvider",
    );

    consoleError.mockRestore();
  });
});
