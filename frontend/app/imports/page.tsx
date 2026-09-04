"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { AppShell } from "@/components/layout/app-shell";
import { ProtectedRoute } from "@/components/shared/protected-route";
import { StatusBadge } from "@/components/shared/status-badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Select } from "@/components/ui/select";
import { extractApiErrorMessage } from "@/lib/api";
import { listImports, previewImport, startImport } from "@/lib/imports-api";
import {
  IMPORT_ENTITY_LABELS,
  IMPORT_ENTITY_TYPES,
  IMPORT_TEMPLATE_COLUMNS,
  type ImportEntityType,
  type ImportPreview,
} from "@/types/import";

const ACTIVE_STATUSES = ["queued", "running"];

function ImportsPageContent() {
  const queryClient = useQueryClient();
  const [entityType, setEntityType] = useState<ImportEntityType>("company");
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [isPreviewing, setIsPreviewing] = useState(false);
  const [isStarting, setIsStarting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const jobsQuery = useQuery({
    queryKey: ["imports"],
    queryFn: () => listImports({ page: 1, page_size: 20 }),
    refetchInterval: (query) =>
      query.state.data?.items.some((j) => ACTIVE_STATUSES.includes(j.status)) ? 2000 : false,
  });

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFile(e.target.files?.[0] ?? null);
    setPreview(null);
    setFormError(null);
    setSuccessMessage(null);
  };

  const onPreview = async () => {
    if (!file) return;
    setFormError(null);
    setSuccessMessage(null);
    setIsPreviewing(true);
    try {
      const result = await previewImport(entityType, file);
      setPreview(result);
    } catch (error) {
      setFormError(extractApiErrorMessage(error, "Could not preview this file"));
    } finally {
      setIsPreviewing(false);
    }
  };

  const onStartImport = async () => {
    if (!file) return;
    setFormError(null);
    setIsStarting(true);
    try {
      await startImport(entityType, file);
      setSuccessMessage("Import queued — track its progress in the table below.");
      setFile(null);
      setPreview(null);
      queryClient.invalidateQueries({ queryKey: ["imports"] });
    } catch (error) {
      setFormError(extractApiErrorMessage(error, "Could not start this import"));
    } finally {
      setIsStarting(false);
    }
  };

  return (
    <AppShell>
      <h1 className="mb-6 text-xl font-semibold text-slate-900">Import data</h1>

      <Card className="mb-6">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Select
            label="What are you importing?"
            value={entityType}
            onChange={(e) => {
              setEntityType(e.target.value as ImportEntityType);
              setFile(null);
              setPreview(null);
            }}
          >
            {IMPORT_ENTITY_TYPES.map((t) => (
              <option key={t} value={t}>
                {IMPORT_ENTITY_LABELS[t]}
              </option>
            ))}
          </Select>
          <div className="flex flex-col gap-1">
            <label className="text-sm font-medium text-slate-700">CSV file</label>
            <input
              type="file"
              accept=".csv,text/csv"
              onChange={onFileChange}
              className="text-sm text-slate-700 file:mr-3 file:rounded-md file:border-0 file:bg-slate-100 file:px-3 file:py-2 file:text-sm file:font-medium file:text-slate-700 hover:file:bg-slate-200"
            />
          </div>
        </div>

        <p className="mt-3 text-xs text-slate-500">
          Expected columns for {IMPORT_ENTITY_LABELS[entityType]}:{" "}
          {IMPORT_TEMPLATE_COLUMNS[entityType].join(", ")}. List-type columns (like tags or
          locations) use a semicolon to separate multiple values.
        </p>

        <div className="mt-4 flex gap-2">
          <Button variant="secondary" onClick={onPreview} disabled={!file} isLoading={isPreviewing}>
            Preview
          </Button>
          <Button
            onClick={onStartImport}
            disabled={!file || !preview?.can_proceed}
            isLoading={isStarting}
          >
            Start import
          </Button>
        </div>

        {formError && (
          <p role="alert" className="mt-3 text-sm text-red-600">
            {formError}
          </p>
        )}
        {successMessage && <p className="mt-3 text-sm text-green-700">{successMessage}</p>}

        {preview && (
          <div className="mt-4 rounded-md border border-slate-200 p-4 text-sm">
            <p className="font-medium text-slate-800">
              {preview.total_rows} row(s) detected — {preview.valid_row_count} valid,{" "}
              {preview.invalid_row_count} invalid
            </p>
            {preview.missing_required_columns.length > 0 && (
              <p className="mt-1 text-red-600">
                Missing required columns: {preview.missing_required_columns.join(", ")}
              </p>
            )}
            {preview.unknown_columns.length > 0 && (
              <p className="mt-1 text-amber-700">
                Unrecognized columns (ignored): {preview.unknown_columns.join(", ")}
              </p>
            )}
            {preview.sample_errors.length > 0 && (
              <div className="mt-2">
                <p className="font-medium text-slate-700">Row errors (sample)</p>
                <ul className="mt-1 list-inside list-disc text-slate-600">
                  {preview.sample_errors.map((e) => (
                    <li key={e.row}>
                      Row {e.row}: {e.errors.join("; ")}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {!preview.can_proceed && preview.missing_required_columns.length === 0 && (
              <p className="mt-2 text-red-600">File has no data rows to import.</p>
            )}
          </div>
        )}
      </Card>

      <h2 className="mb-3 text-lg font-semibold text-slate-900">Import history</h2>
      {jobsQuery.isLoading && <p className="text-sm text-slate-500">Loading…</p>}
      {jobsQuery.data && jobsQuery.data.items.length === 0 && (
        <p className="rounded-md border border-dashed border-slate-300 p-8 text-center text-sm text-slate-500">
          No imports yet.
        </p>
      )}
      {jobsQuery.data && jobsQuery.data.items.length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-slate-200 bg-slate-50 text-slate-600">
              <tr>
                <th className="px-4 py-2">File</th>
                <th className="px-4 py-2">Type</th>
                <th className="px-4 py-2">Status</th>
                <th className="px-4 py-2">Progress</th>
                <th className="px-4 py-2">Created</th>
                <th className="px-4 py-2">Skipped</th>
                <th className="px-4 py-2">Errors</th>
                <th className="px-4 py-2">Started</th>
              </tr>
            </thead>
            <tbody>
              {jobsQuery.data.items.map((job) => (
                <tr key={job.id} className="border-b border-slate-100 align-top last:border-0">
                  <td className="px-4 py-2 text-slate-800">{job.file_name}</td>
                  <td className="px-4 py-2 text-slate-600 capitalize">
                    {IMPORT_ENTITY_LABELS[job.entity_type]}
                  </td>
                  <td className="px-4 py-2">
                    <StatusBadge value={job.status} />
                  </td>
                  <td className="px-4 py-2 text-slate-600">
                    {job.processed_rows}/{job.total_rows} ({job.progress_percentage}%)
                  </td>
                  <td className="px-4 py-2 text-slate-600">{job.created_count}</td>
                  <td className="px-4 py-2 text-slate-600">{job.skipped_count}</td>
                  <td className="px-4 py-2 text-slate-600">
                    {job.error_count > 0 ? (
                      <details>
                        <summary className="cursor-pointer text-red-600">
                          {job.error_count}
                        </summary>
                        <ul className="mt-1 list-inside list-disc text-xs text-slate-600">
                          {job.row_errors.slice(0, 10).map((e) => (
                            <li key={e.row}>
                              Row {e.row}: {e.errors.join("; ")}
                            </li>
                          ))}
                        </ul>
                      </details>
                    ) : (
                      0
                    )}
                  </td>
                  <td className="px-4 py-2 text-slate-500">
                    {new Date(job.created_at).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </AppShell>
  );
}

export default function ImportsPage() {
  return (
    <ProtectedRoute>
      <ImportsPageContent />
    </ProtectedRoute>
  );
}
