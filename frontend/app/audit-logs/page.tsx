"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { AppShell } from "@/components/layout/app-shell";
import { ProtectedRoute } from "@/components/shared/protected-route";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { listAuditLogs } from "@/lib/admin-api";

function AuditLogsPageContent() {
  const [action, setAction] = useState("");
  const [page, setPage] = useState(1);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["audit-logs", { action, page }],
    queryFn: () => listAuditLogs({ action: action || undefined, page, page_size: 20 }),
  });

  return (
    <AppShell>
      <h1 className="mb-6 text-xl font-semibold text-slate-900">Audit logs</h1>

      <div className="mb-4 max-w-xs">
        <Input
          placeholder="Filter by action, e.g. lead.created"
          value={action}
          onChange={(e) => {
            setPage(1);
            setAction(e.target.value);
          }}
        />
      </div>

      {isLoading && <p className="text-sm text-slate-500">Loading audit logs…</p>}
      {isError && <p className="text-sm text-red-600">Could not load audit logs.</p>}
      {!isLoading && data?.items.length === 0 && (
        <p className="rounded-md border border-dashed border-slate-300 p-8 text-center text-sm text-slate-500">
          No audit log entries yet.
        </p>
      )}

      {data && data.items.length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-slate-200 bg-slate-50 text-slate-600">
              <tr>
                <th className="px-4 py-2">Action</th>
                <th className="px-4 py-2">Resource</th>
                <th className="px-4 py-2">IP address</th>
                <th className="px-4 py-2">When</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((entry) => (
                <tr key={entry.id} className="border-b border-slate-100 last:border-0">
                  <td className="px-4 py-2 font-medium text-slate-800">{entry.action}</td>
                  <td className="px-4 py-2 text-slate-600">
                    {entry.resource_type}
                    {entry.resource_id && (
                      <span className="text-slate-400"> · {entry.resource_id.slice(0, 8)}</span>
                    )}
                  </td>
                  <td className="px-4 py-2 text-slate-500">{entry.ip_address || "—"}</td>
                  <td className="px-4 py-2 text-slate-500">
                    {new Date(entry.created_at).toLocaleString()}
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
            entries)
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

export default function AuditLogsPage() {
  return (
    <ProtectedRoute>
      <AuditLogsPageContent />
    </ProtectedRoute>
  );
}
