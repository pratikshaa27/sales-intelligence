"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";

import { AppShell } from "@/components/layout/app-shell";
import { ProtectedRoute } from "@/components/shared/protected-route";
import { StatusBadge } from "@/components/shared/status-badge";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import { JOB_STATUS_ACTIVE, JOB_TYPE_LABELS, listJobs } from "@/lib/research-api";

function ResearchJobsContent() {
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);

  const { data, isLoading } = useQuery({
    queryKey: ["jobs", { status, page }],
    queryFn: () => listJobs({ status: status || undefined, page, page_size: 20 }),
    refetchInterval: (query) =>
      query.state.data?.items.some((j) => JOB_STATUS_ACTIVE.includes(j.status)) ? 3000 : false,
  });

  return (
    <AppShell>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-xl font-semibold text-slate-900">Research jobs</h1>
        <Link href="/companies/discover">
          <Button variant="secondary">Discover companies</Button>
        </Link>
      </div>

      <div className="mb-4 max-w-[220px]">
        <Select
          value={status}
          onChange={(e) => {
            setPage(1);
            setStatus(e.target.value);
          }}
        >
          <option value="">All statuses</option>
          <option value="queued">Queued</option>
          <option value="running">Running</option>
          <option value="completed">Completed</option>
          <option value="failed">Failed</option>
          <option value="cancelled">Cancelled</option>
        </Select>
      </div>

      {isLoading && <p className="text-sm text-slate-500">Loading jobs…</p>}
      {!isLoading && data?.items.length === 0 && (
        <p className="rounded-md border border-dashed border-slate-300 p-8 text-center text-sm text-slate-500">
          No research jobs yet. Run research from a company page or start a discovery job.
        </p>
      )}

      {data && data.items.length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-slate-200 bg-slate-50 text-slate-600">
              <tr>
                <th className="px-4 py-2">Type</th>
                <th className="px-4 py-2">Status</th>
                <th className="px-4 py-2">Step</th>
                <th className="px-4 py-2">Created</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((job) => (
                <tr key={job.id} className="border-b border-slate-100 last:border-0">
                  <td className="px-4 py-2">
                    <Link
                      href={`/research-jobs/${job.id}`}
                      className="font-medium text-brand-700 hover:underline"
                    >
                      {JOB_TYPE_LABELS[job.job_type]}
                    </Link>
                  </td>
                  <td className="px-4 py-2">
                    <StatusBadge value={job.status} />
                  </td>
                  <td className="px-4 py-2 text-slate-600">{job.current_step || "—"}</td>
                  <td className="px-4 py-2 text-slate-500">
                    {new Date(job.created_at).toLocaleString()}
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
            Page {data.pagination.page} of {data.pagination.total_pages}
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

export default function ResearchJobsPage() {
  return (
    <ProtectedRoute>
      <ResearchJobsContent />
    </ProtectedRoute>
  );
}
