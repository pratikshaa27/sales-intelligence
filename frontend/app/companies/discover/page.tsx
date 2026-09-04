"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";
import { Controller, useForm } from "react-hook-form";

import { AppShell } from "@/components/layout/app-shell";
import { ProtectedRoute } from "@/components/shared/protected-route";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { TagInput } from "@/components/ui/tag-input";
import { extractApiErrorMessage } from "@/lib/api";
import { discoverCompanies, getJob, JOB_STATUS_ACTIVE } from "@/lib/research-api";
import { discoverCompaniesFormSchema, type DiscoverCompaniesFormValues } from "@/lib/validations";
import type { DiscoveredCompanyCandidate } from "@/types/research";

function DiscoverCompaniesContent() {
  const [jobId, setJobId] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    control,
    formState: { isSubmitting },
  } = useForm<DiscoverCompaniesFormValues>({
    resolver: zodResolver(discoverCompaniesFormSchema),
    defaultValues: {
      industry: "",
      location: "",
      company_size: "",
      keywords: [],
      number_of_companies: 5,
    },
  });

  const jobQuery = useQuery({
    queryKey: ["job", jobId],
    queryFn: () => getJob(jobId as string),
    enabled: Boolean(jobId),
    refetchInterval: (query) =>
      query.state.data && JOB_STATUS_ACTIVE.includes(query.state.data.status) ? 1500 : false,
  });

  const onSubmit = async (values: DiscoverCompaniesFormValues) => {
    setFormError(null);
    try {
      const job = await discoverCompanies(values);
      setJobId(job.id);
    } catch (error) {
      setFormError(extractApiErrorMessage(error, "Could not start discovery"));
    }
  };

  const summary = jobQuery.data?.result_summary as
    | { candidates?: DiscoveredCompanyCandidate[]; is_mock_data?: boolean; provider?: string }
    | undefined;

  return (
    <AppShell>
      <h1 className="mb-2 text-xl font-semibold text-slate-900">Discover companies</h1>
      <p className="mb-6 text-sm text-slate-500">
        Finds candidate companies matching your criteria for review — nothing is added to your
        company list automatically (spec §6: discovery results always need human review before being
        saved).
      </p>

      <Card className="mb-6">
        <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4" noValidate>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <Input label="Industry" {...register("industry")} />
            <Input label="Location" {...register("location")} />
            <Input label="Company size" placeholder="e.g. 51-200" {...register("company_size")} />
          </div>
          <Controller
            control={control}
            name="keywords"
            render={({ field }) => (
              <TagInput
                name={field.name}
                label="Keywords"
                value={field.value}
                onChange={field.onChange}
              />
            )}
          />
          <Input
            label="Number of companies"
            type="number"
            min={1}
            max={20}
            {...register("number_of_companies", { valueAsNumber: true })}
            className="max-w-[160px]"
          />
          {formError && (
            <p role="alert" className="text-sm text-red-600">
              {formError}
            </p>
          )}
          <Button
            type="submit"
            isLoading={
              isSubmitting || (jobQuery.data && JOB_STATUS_ACTIVE.includes(jobQuery.data.status))
            }
            className="self-start"
          >
            Discover companies
          </Button>
        </form>
      </Card>

      {jobQuery.data && (
        <Card>
          <h2 className="mb-3 text-lg font-semibold text-slate-900">Results</h2>
          {JOB_STATUS_ACTIVE.includes(jobQuery.data.status) && (
            <p className="text-sm text-slate-500">Searching… {jobQuery.data.current_step}</p>
          )}
          {jobQuery.data.status === "failed" && (
            <p className="text-sm text-red-600">{jobQuery.data.error_message}</p>
          )}
          {jobQuery.data.status === "completed" && summary?.candidates && (
            <>
              {summary.is_mock_data && (
                <p className="mb-3 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800">
                  These are illustrative placeholder candidates from the mock discovery provider —
                  configure a real data provider before using discovery for actual prospecting.
                </p>
              )}
              <ul className="flex flex-col gap-3">
                {summary.candidates.map((candidate) => (
                  <li
                    key={candidate.website}
                    className="rounded-md border border-slate-200 p-3 text-sm"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-medium text-slate-900">{candidate.name}</span>
                      {candidate.already_exists ? (
                        <span className="text-xs text-slate-500">Already in your companies</span>
                      ) : (
                        <Link
                          href={`/companies/new?website=${encodeURIComponent(candidate.website)}&name=${encodeURIComponent(candidate.name)}`}
                          className="text-xs text-brand-700 hover:underline"
                        >
                          Add to companies
                        </Link>
                      )}
                    </div>
                    <p className="text-slate-500">{candidate.website}</p>
                    <p className="mt-1 text-xs text-slate-500">{candidate.rationale}</p>
                  </li>
                ))}
              </ul>
            </>
          )}
        </Card>
      )}
    </AppShell>
  );
}

export default function DiscoverCompaniesPage() {
  return (
    <ProtectedRoute>
      <DiscoverCompaniesContent />
    </ProtectedRoute>
  );
}
