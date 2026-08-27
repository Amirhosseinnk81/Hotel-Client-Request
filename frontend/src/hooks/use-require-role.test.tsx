import { renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const replaceMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: replaceMock }),
}));

// useRequireRole only reads {isLoading, isAuthenticated, role} off useAuth,
// so mocking the module directly is simpler and more robust than wrapping
// every test in a real <AuthProvider> (which reads from localStorage on
// mount and would need its own set of stubs).
const useAuthMock = vi.fn();
vi.mock("@/contexts/auth-context", () => ({
  useAuth: () => useAuthMock(),
}));

// Imported after the mocks above so the hook picks up the mocked modules.
const { useRequireRole } = await import("./use-require-role");

describe("useRequireRole", () => {
  beforeEach(() => {
    replaceMock.mockClear();
    useAuthMock.mockReset();
  });

  it("renders nothing and does not redirect while auth is still loading", () => {
    useAuthMock.mockReturnValue({ isLoading: true, isAuthenticated: false, role: null });

    const { result } = renderHook(() => useRequireRole(["GUEST"], "/guest/login"));

    expect(result.current).toBe(false);
    expect(replaceMock).not.toHaveBeenCalled();
  });

  it("allows rendering once loaded, authenticated, with an allowed role", () => {
    useAuthMock.mockReturnValue({ isLoading: false, isAuthenticated: true, role: "GUEST" });

    const { result } = renderHook(() => useRequireRole(["GUEST"], "/guest/login"));

    expect(result.current).toBe(true);
    expect(replaceMock).not.toHaveBeenCalled();
  });

  it("redirects when loaded but not authenticated", () => {
    useAuthMock.mockReturnValue({ isLoading: false, isAuthenticated: false, role: null });

    const { result } = renderHook(() => useRequireRole(["GUEST"], "/guest/login"));

    expect(result.current).toBe(false);
    expect(replaceMock).toHaveBeenCalledWith("/guest/login");
  });

  it("redirects when authenticated but with a role outside the allow-list", () => {
    useAuthMock.mockReturnValue({ isLoading: false, isAuthenticated: true, role: "OPERATOR" });

    const { result } = renderHook(() => useRequireRole(["GUEST"], "/guest/login"));

    expect(result.current).toBe(false);
    expect(replaceMock).toHaveBeenCalledWith("/guest/login");
  });

  it("accepts any role included in a multi-role allow-list", () => {
    useAuthMock.mockReturnValue({ isLoading: false, isAuthenticated: true, role: "ADMIN" });

    const { result } = renderHook(() =>
      useRequireRole(["OPERATOR", "ADMIN"], "/operator/login")
    );

    expect(result.current).toBe(true);
    expect(replaceMock).not.toHaveBeenCalled();
  });

  it("never redirects when skip is true, regardless of auth state", () => {
    useAuthMock.mockReturnValue({ isLoading: false, isAuthenticated: false, role: null });

    const { result } = renderHook(() =>
      useRequireRole(["GUEST"], "/guest/login", /* skip */ true)
    );

    expect(result.current).toBe(true);
    expect(replaceMock).not.toHaveBeenCalled();
  });
});
