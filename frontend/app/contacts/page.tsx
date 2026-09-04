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
import { listContacts } from "@/lib/contacts-api";
import { hasPermission } from "@/lib/permissions";

function ContactsPageContent() {
  const { me } = useAuth();
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["contacts", { search, page }],
    queryFn: () => listContacts({ search: search || undefined, page, page_size: 20 }),
  });

  const canCreate = hasPermission(me?.permissions, "contacts.create");

  return (
    <AppShell>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-xl font-semibold text-slate-900">Contacts</h1>
        {canCreate && (
          <Link href="/contacts/new">
            <Button>New contact</Button>
          </Link>
        )}
      </div>

      <div className="mb-4">
        <Input
          placeholder="Search by name or job title"
          value={search}
          onChange={(e) => {
            setPage(1);
            setSearch(e.target.value);
          }}
        />
      </div>

      {isLoading && <p className="text-sm text-slate-500">Loading contacts…</p>}
      {isError && <p className="text-sm text-red-600">Could not load contacts.</p>}
      {!isLoading && data?.items.length === 0 && (
        <p className="rounded-md border border-dashed border-slate-300 p-8 text-center text-sm text-slate-500">
          No contacts yet. {canCreate && "Add your first one to get started."}
        </p>
      )}

      {data && data.items.length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-slate-200 bg-slate-50 text-slate-600">
              <tr>
                <th className="px-4 py-2">Name</th>
                <th className="px-4 py-2">Company</th>
                <th className="px-4 py-2">Product(s)</th>
                <th className="px-4 py-2">Job title</th>
                <th className="px-4 py-2">Seniority</th>
                <th className="px-4 py-2">Confidence</th>
                <th className="px-4 py-2">Verification</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((contact) => (
                <tr key={contact.id} className="border-b border-slate-100 last:border-0">
                  <td className="px-4 py-2">
                    <Link
                      href={`/contacts/${contact.id}`}
                      className="font-medium text-brand-700 hover:underline"
                    >
                      {contact.full_name}
                    </Link>
                  </td>
                  <td className="px-4 py-2">
                    <Link
                      href={`/companies/${contact.company_id}`}
                      className="text-slate-600 hover:text-brand-700 hover:underline"
                    >
                      {contact.company_name}
                    </Link>
                  </td>
                  <td className="px-4 py-2">
                    {contact.products.length > 0 ? (
                      <div className="flex flex-wrap gap-1">
                        {contact.products.map((product) => (
                          <span
                            key={product}
                            className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-700"
                          >
                            {product}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <span className="text-slate-400">No lead yet</span>
                    )}
                  </td>
                  <td className="px-4 py-2 text-slate-600">{contact.job_title || "—"}</td>
                  <td className="px-4 py-2 text-slate-600">{contact.seniority || "—"}</td>
                  <td className="px-4 py-2 text-slate-600">{contact.confidence_score}</td>
                  <td className="px-4 py-2">
                    <StatusBadge value={contact.verification_status} />
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
            contacts)
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

export default function ContactsPage() {
  return (
    <ProtectedRoute>
      <ContactsPageContent />
    </ProtectedRoute>
  );
}
