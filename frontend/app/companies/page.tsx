"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";

import { AppShell } from "@/components/layout/app-shell";
import { ProtectedRoute } from "@/components/shared/protected-route";
import { StatusBadge } from "@/components/shared/status-badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAuth } from "@/hooks/use-auth";
import { listCompanies } from "@/lib/companies-api";
import { hasPermission } from "@/lib/permissions";

function CompaniesPageContent() {
  const { me } = useAuth();
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["companies", { search, page }],
    queryFn: () => listCompanies({ search: search || undefined, page, page_size: 20 }),
  });

  const canCreate = hasPermission(me?.permissions, "companies.create");

  return (
    <AppShell>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-xl font-semibold text-slate-900">Companies</h1>
        {canCreate && (
          <Link href="/companies/new">
            <Button>New company</Button>
          </Link>
        )}
      </div>

      <div className="mb-4">
        <Input
          placeholder="Search by name or domain"
          value={search}
          onChange={(e) => {
            setPage(1);
            setSearch(e.target.value);
          }}
        />
      </div>

      {isLoading && <p className="text-sm text-slate-500">Loading companies…</p>}
      {isError && <p className="text-sm text-red-600">Could not load companies.</p>}
      {!isLoading && data?.items.length === 0 && (
        <p className="rounded-md border border-dashed border-slate-300 p-8 text-center text-sm text-slate-500">
          No companies yet. {canCreate && "Add your first one to get started."}
        </p>
      )}

      {data && data.items.length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-slate-200 bg-slate-50 text-slate-600">
              <tr>
                <th className="px-4 py-2">Name</th>
                <th className="px-4 py-2">Domain</th>
                <th className="px-4 py-2">Industry</th>
                <th className="px-4 py-2">Size</th>
                <th className="px-4 py-2">Confidence</th>
                <th className="px-4 py-2">Research</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((company) => (
                <tr key={company.id} className="border-b border-slate-100 last:border-0">
                  <td className="px-4 py-2">
                    <Link
                      href={`/companies/${company.id}`}
                      className="font-medium text-brand-700 hover:underline"
                    >
                      {company.name}
                    </Link>
                  </td>
                  <td className="px-4 py-2 text-slate-600">{company.domain}</td>
                  <td className="px-4 py-2 text-slate-600">{company.industry || "—"}</td>
                  <td className="px-4 py-2 text-slate-600">{company.company_size || "—"}</td>
                  <td className="px-4 py-2 text-slate-600">{company.confidence_score}</td>
                  <td className="px-4 py-2">
                    <StatusBadge value={company.research_status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {data && data.pagination.total_pages > 1 && (
        <div className="mt-4 flex items-center justify-between text-sm text-slate-600">
          <span>
            Page {data.pagination.page} of {data.pagination.total_pages} ({data.pagination.total}{" "}
            companies)
          </span>
          <div className="flex gap-2">
            <Button
              variant="secondary"
              disabled={page <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
            >
              Previous
            </Button>
            <Button
              variant="secondary"
              disabled={page >= data.pagination.total_pages}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
            </Button>
          </div>
        </div>
      )}
    </AppShell>
  );
}

export default function CompaniesPage() {
  return (
    <ProtectedRoute>
      <CompaniesPageContent />
    </ProtectedRoute>
  );
}
