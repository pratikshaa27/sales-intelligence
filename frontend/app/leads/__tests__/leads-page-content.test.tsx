import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { LeadsPageContent } from "@/app/leads/leads-page-content";
import { listLeads } from "@/lib/leads-api";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock("@/hooks/use-auth", () => ({
  useAuth: () => ({
    me: {
      user: { full_name: "Org Admin" },
      organization_name: "Acme Inc",
      role: "org_admin",
      permissions: ["leads.view", "leads.create", "leads.export"],
    },
    logout: vi.fn(),
  }),
}));

vi.mock("@/lib/leads-api", () => ({
  listLeads: vi.fn(),
  exportLeads: vi.fn(),
}));

function renderWithQueryClient(ui: ReactNode) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>,
  );
}

const emptyPage = { items: [], pagination: { page: 1, page_size: 20, total: 0, total_pages: 0 } };

describe("LeadsPageContent loading/empty/populated states", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("shows a loading message while the query is in flight", () => {
    vi.mocked(listLeads).mockReturnValue(new Promise(() => {})); // never resolves
    renderWithQueryClient(<LeadsPageContent />);
    expect(screen.getByText(/loading leads/i)).toBeInTheDocument();
  });

  it("shows an empty-state message with a create hint once loaded with no leads", async () => {
    vi.mocked(listLeads).mockResolvedValue(emptyPage);
    renderWithQueryClient(<LeadsPageContent />);
    await waitFor(() => expect(screen.getByText(/no leads yet/i)).toBeInTheDocument());
    expect(screen.getByText(/create your first one/i)).toBeInTheDocument();
  });

  it("renders a table row per lead once the query resolves with data", async () => {
    vi.mocked(listLeads).mockResolvedValue({
      items: [
        {
          id: "11111111-1111-1111-1111-111111111111",
          company_id: "22222222-2222-2222-2222-222222222222",
          product_id: "33333333-3333-3333-3333-333333333333",
          name: "Acme - Sales Copilot",
          status: "new",
          priority: "high",
          total_score: 82,
          assigned_to: null,
          created_at: "2026-01-01T00:00:00Z",
        },
      ],
      pagination: { page: 1, page_size: 20, total: 1, total_pages: 1 },
    });
    renderWithQueryClient(<LeadsPageContent />);
    await waitFor(() => expect(screen.getByText("Acme - Sales Copilot")).toBeInTheDocument());
    expect(screen.getByText("82/100")).toBeInTheDocument();
  });
});
