import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ProtectedRoute } from "@/components/shared/protected-route";

const replaceMock = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: replaceMock }),
}));

const useAuthMock = vi.fn();
vi.mock("@/hooks/use-auth", () => ({
  useAuth: () => useAuthMock(),
}));

describe("ProtectedRoute", () => {
  afterEach(() => {
    replaceMock.mockClear();
  });

  it("shows a loading state while bootstrapping and does not redirect yet", () => {
    useAuthMock.mockReturnValue({ me: undefined, isBootstrapping: true, isLoading: false });
    render(
      <ProtectedRoute>
        <div>Secret content</div>
      </ProtectedRoute>,
    );
    expect(screen.getByText(/loading/i)).toBeInTheDocument();
    expect(replaceMock).not.toHaveBeenCalled();
  });

  it("redirects to /login and renders nothing when there is no authenticated user", () => {
    useAuthMock.mockReturnValue({ me: undefined, isBootstrapping: false, isLoading: false });
    const { container } = render(
      <ProtectedRoute>
        <div>Secret content</div>
      </ProtectedRoute>,
    );
    expect(replaceMock).toHaveBeenCalledWith("/login");
    expect(container).toBeEmptyDOMElement();
  });

  it("renders the protected children once an authenticated user is loaded", () => {
    useAuthMock.mockReturnValue({
      me: { user: { full_name: "Ada Admin" } },
      isBootstrapping: false,
      isLoading: false,
    });
    render(
      <ProtectedRoute>
        <div>Secret content</div>
      </ProtectedRoute>,
    );
    expect(screen.getByText("Secret content")).toBeInTheDocument();
    expect(replaceMock).not.toHaveBeenCalled();
  });
});
