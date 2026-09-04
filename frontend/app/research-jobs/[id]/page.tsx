"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { useState } from "react";

import { AppShell } from "@/components/layout/app-shell";
import { ProtectedRoute } from "@/components/shared/protected-route";
import { StatusBadge } from "@/components/shared/status-badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { useAuth } from "@/hooks/use-auth";
import { extractApiErrorMessage } from "@/lib/api";
import { hasPermission } from "@/lib/permissions";
import { cancelJob, getJob, JOB_STATUS_ACTIVE, JOB_TYPE_LABELS } from "@/lib/research-api";

function JobDetailContent() {
  const { me } = useAuth();
  const params = useParams<{ id: string }>();
  const jobId = params.id;
  const queryClient = useQueryClient();
  const [actionError, setActionError] = useState<string | null>(null);

  const jobQuery = useQuery({
    queryKey: ["job", jobId],
    queryFn: () => getJob(jobId),
    refetchInterval: (query) =>
      query.state.data && JOB_STATUS_ACTIVE.includes(query.state.data.status) ? 1500 : false,
  });

  const canCancel = hasPermission(me?.permissions, "companies.edit");
  const job = jobQuery.data;

  const onCancel = async () => {
    setActionError(null);
    try {
      await cancelJob(jobId);
      queryClient.invalidateQueries({ queryKey: ["job", jobId] });
    } catch (error) {
      setActionError(extractApiErrorMessage(error, "Could not cancel job"));
    }
  };

  if (jobQuery.isLoading) {
    return (
      <AppShell>
        <p className="text-sm text-slate-500">Loading job…</p>
      </AppShell>
    );
  }

  if (!job) {
    return (
      <AppShell>
        <p className="text-sm text-red-600">Job not found.</p>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-semibold text-slate-900">
              {JOB_TYPE_LABELS[job.job_type]}
            </h1>
            <StatusBadge value={job.status} />
          </div>
          <p className="text-sm text-slate-500">Created {new Date(job.created_at).toLocaleString()}</p>
        </div>
        {canCancel && JOB_STATUS_ACTIVE.includes(job.status) && (
          <Button variant="destructive" onClick={onCancel}>
            Cancel job
          </Button>
        )}
      </div>

      {actionError && (
        <p role="alert" className="mb-4 text-sm text-red-600">
          {actionError}
        </p>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <h2 className="mb-2 text-lg font-semibold text-slate-900">Progress</h2>
          <p className="text-sm text-slate-700">{job.current_step || "Queued"}</p>
          <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-slate-100">
            <div
              className="h-full bg-brand-600 transition-all"
              style={{ width: `${job.progress_percentage}%` }}
            />
          </div>
          {job.error_message && (
            <p className="mt-3 text-sm text-red-600">{job.error_message}</p>
          )}
          <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
            <div>
              <dt className="text-slate-500">Started</dt>
              <dd className="text-slate-800">
                {job.started_at ? new Date(job.started_at).toLocaleString() : "—"}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">Completed</dt>
              <dd className="text-slate-800">
                {job.completed_at ? new Date(job.completed_at).toLocaleString() : "—"}
              </dd>
            </div>
          </dl>
        </Card>

        <Card>
          <h2 className="mb-2 text-lg font-semibold text-slate-900">Logs</h2>
          {job.logs.length ? (
            <ul className="flex flex-col gap-1 text-sm text-slate-700">
              {job.logs.map((line, i) => (
                <li key={i} className="font-mono text-xs">
                  {line}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-slate-500">No logs yet.</p>
          )}
        </Card>
      </div>

      {Object.keys(job.result_summary).length > 0 && (
        <Card className="mt-6">
          <h2 className="mb-2 text-lg font-semibold text-slate-900">Result summary</h2>
          <pre className="overflow-x-auto whitespace-pre-wrap text-xs text-slate-700">
            {JSON.stringify(job.result_summary, null, 2)}
          </pre>
        </Card>
      )}
    </AppShell>
  );
}

export default function JobDetailPage() {
  return (
    <ProtectedRoute>
      <JobDetailContent />
    </ProtectedRoute>
  );
}
