import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AppShell } from "@/components/layout/app-shell";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

const useAuthMock = vi.fn();
vi.mock("@/hooks/use-auth", () => ({
  useAuth: () => useAuthMock(),
}));

describe("AppShell navigation (permission-based rendering)", () => {
  it("hides nav items the current role has no permission for", () => {
    useAuthMock.mockReturnValue({
      me: {
        user: { full_name: "Rep User" },
        organization_name: "Acme Inc",
        role: "sales_representative",
        // A sales rep has leads.view but not members.view (per app/core/rbac_data.py) —
        // "Team" must not render for this role.
        permissions: ["leads.view", "products.view", "companies.view"],
      },
      logout: vi.fn(),
    });

    render(
      <AppShell>
        <div>Page content</div>
      </AppShell>,
    );

    expect(screen.getByText("Leads")).toBeInTheDocument();
    expect(screen.getByText("Products")).toBeInTheDocument();
    expect(screen.queryByText("Team")).not.toBeInTheDocument();
  });

  it("shows every permission-gated nav item for a fully-permissioned role", () => {
    useAuthMock.mockReturnValue({
      me: {
        user: { full_name: "Org Admin" },
        organization_name: "Acme Inc",
        role: "org_admin",
        permissions: [
          "products.view",
          "companies.view",
          "contacts.view",
          "leads.view",
          "leads.create",
          "members.view",
        ],
      },
      logout: vi.fn(),
    });

    render(
      <AppShell>
        <div>Page content</div>
      </AppShell>,
    );

    expect(screen.getByText("Team")).toBeInTheDocument();
    expect(screen.getByText("Import data")).toBeInTheDocument();
  });

  it("always renders the always-visible Dashboard link regardless of permissions", () => {
    useAuthMock.mockReturnValue({
      me: {
        user: { full_name: "Read Only User" },
        organization_name: "Acme Inc",
        role: "read_only",
        permissions: [],
      },
      logout: vi.fn(),
    });

    render(
      <AppShell>
        <div>Page content</div>
      </AppShell>,
    );

    expect(screen.getByText("Dashboard")).toBeInTheDocument();
    expect(screen.queryByText("Team")).not.toBeInTheDocument();
  });
});
