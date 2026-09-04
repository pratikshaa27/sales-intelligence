"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";

import { AppShell } from "@/components/layout/app-shell";
import { StatusBadge } from "@/components/shared/status-badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { useAuth } from "@/hooks/use-auth";
import { extractApiErrorMessage } from "@/lib/api";
import { exportLeads, listLeads } from "@/lib/leads-api";
import { hasPermission } from "@/lib/permissions";
import { LEAD_STATUSES, type LeadPriority, type LeadStatus } from "@/types/lead";

export function LeadsPageContent() {
  const { me } = useAuth();
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<LeadStatus | "">("");
  const [priority, setPriority] = useState<LeadPriority | "">("");
  const [page, setPage] = useState(1);
  const [isExporting, setIsExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["leads", { search, status, priority, page }],
    queryFn: () =>
      listLeads({
        search: search || undefined,
        status: status || undefined,
        priority: priority || undefined,
        page,
        page_size: 20,
      }),
  });

  const canCreate = hasPermission(me?.permissions, "leads.create");
  const canExport = hasPermission(me?.permissions, "leads.export");

  const onExport = async (format: "csv" | "csv_excel" | "json") => {
    setExportError(null);
    setIsExporting(true);
    try {
      await exportLeads({
        format,
        status: status || undefined,
        priority: priority || undefined,
      });
    } catch (error) {
      setExportError(extractApiErrorMessage(error, "Could not export leads"));
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <AppShell>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-xl font-semibold text-slate-900">Leads</h1>
        <div className="flex gap-2">
          {canExport && (
            <>
              <Button variant="secondary" disabled={isExporting} onClick={() => onExport("csv")}>
                Export CSV
              </Button>
              <Button
                variant="secondary"
                disabled={isExporting}
                onClick={() => onExport("csv_excel")}
              >
                Export CSV (Excel)
              </Button>
              <Button variant="secondary" disabled={isExporting} onClick={() => onExport("json")}>
                Export JSON
              </Button>
            </>
          )}
          {canCreate && (
            <Link href="/leads/new">
              <Button>New lead</Button>
            </Link>
          )}
        </div>
      </div>

      {exportError && (
        <p role="alert" className="mb-4 text-sm text-red-600">
          {exportError}
        </p>
      )}

      <div className="mb-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
        <Input
          placeholder="Search by name"
          value={search}
          onChange={(e) => {
            setPage(1);
            setSearch(e.target.value);
          }}
        />
        <Select
          value={status}
          onChange={(e) => {
            setPage(1);
            setStatus(e.target.value as LeadStatus | "");
          }}
        >
          <option value="">All statuses</option>
          {LEAD_STATUSES.map((s) => (
            <option key={s} value={s}>
              {s.replace(/_/g, " ")}
            </option>
          ))}
        </Select>
        <Select
          value={priority}
          onChange={(e) => {
            setPage(1);
            setPriority(e.target.value as LeadPriority | "");
          }}
        >
          <option value="">All priorities</option>
          <option value="low">Low</option>
          <option value="medium">Medium</option>
          <option value="high">High</option>
          <option value="critical">Critical</option>
        </Select>
      </div>

      {isLoading && <p className="text-sm text-slate-500">Loading leads…</p>}
      {isError && <p className="text-sm text-red-600">Could not load leads.</p>}
      {!isLoading && data?.items.length === 0 && (
        <p className="rounded-md border border-dashed border-slate-300 p-8 text-center text-sm text-slate-500">
          No leads yet. {canCreate && "Create your first one to get started."}
        </p>
      )}

      {data && data.items.length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-slate-200 bg-slate-50 text-slate-600">
              <tr>
                <th className="px-4 py-2">Name</th>
                <th className="px-4 py-2">Score</th>
                <th className="px-4 py-2">Priority</th>
                <th className="px-4 py-2">Status</th>
                <th className="px-4 py-2">Created</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((lead) => (
                <tr key={lead.id} className="border-b border-slate-100 last:border-0">
                  <td className="px-4 py-2">
                    <Link
                      href={`/leads/${lead.id}`}
                      className="font-medium text-brand-700 hover:underline"
                    >
                      {lead.name}
                    </Link>
                  </td>
                  <td className="px-4 py-2 text-slate-600">{lead.total_score}/100</td>
                  <td className="px-4 py-2">
                    <StatusBadge value={lead.priority} />
                  </td>
                  <td className="px-4 py-2">
                    <StatusBadge value={lead.status} />
                  </td>
                  <td className="px-4 py-2 text-slate-500">
                    {new Date(lead.created_at).toLocaleDateString()}
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
            leads)
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
