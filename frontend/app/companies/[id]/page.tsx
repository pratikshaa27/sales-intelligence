"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { AppShell } from "@/components/layout/app-shell";
import { ProtectedRoute } from "@/components/shared/protected-route";
import { StatusBadge } from "@/components/shared/status-badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useAuth } from "@/hooks/use-auth";
import { extractApiErrorMessage } from "@/lib/api";
import {
  addCompanySource,
  deleteCompany,
  deleteCompanySource,
  getCompany,
  listCompanySources,
} from "@/lib/companies-api";
import { listContacts } from "@/lib/contacts-api";
import { hasPermission } from "@/lib/permissions";
import {
  getJob,
  JOB_STATUS_ACTIVE,
  listCompanyEvidence,
  startCompanyResearch,
} from "@/lib/research-api";

function TagList({ label, values }: { label: string; values: string[] }) {
  if (values.length === 0) return null;
  return (
    <div>
      <p className="text-sm font-medium text-slate-500">{label}</p>
      <div className="mt-1 flex flex-wrap gap-1.5">
        {values.map((v) => (
          <span key={v} className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-700">
            {v}
          </span>
        ))}
      </div>
    </div>
  );
}

function CompanyDetailContent() {
  const { me } = useAuth();
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const companyId = params.id;
  const queryClient = useQueryClient();
  const [actionError, setActionError] = useState<string | null>(null);
  const [newSourceUrl, setNewSourceUrl] = useState("");
  const [activeJobId, setActiveJobId] = useState<string | null>(null);

  const companyQuery = useQuery({
    queryKey: ["company", companyId],
    queryFn: () => getCompany(companyId),
  });
  const sourcesQuery = useQuery({
    queryKey: ["company-sources", companyId],
    queryFn: () => listCompanySources(companyId),
  });
  const contactsQuery = useQuery({
    queryKey: ["contacts", { company_id: companyId }],
    queryFn: () => listContacts({ company_id: companyId, page: 1, page_size: 50 }),
  });
  const evidenceQuery = useQuery({
    queryKey: ["company-evidence", companyId],
    queryFn: () => listCompanyEvidence(companyId),
  });
  const jobQuery = useQuery({
    queryKey: ["job", activeJobId],
    queryFn: () => getJob(activeJobId as string),
    enabled: Boolean(activeJobId),
    refetchInterval: (query) =>
      query.state.data && JOB_STATUS_ACTIVE.includes(query.state.data.status) ? 1500 : false,
  });

  const canEdit = hasPermission(me?.permissions, "companies.edit");
  const canDelete = hasPermission(me?.permissions, "companies.delete");
  const canResearch = hasPermission(me?.permissions, "companies.research");
  const canCreateContact = hasPermission(me?.permissions, "contacts.create");

  const company = companyQuery.data;
  const job = jobQuery.data;
  const settledJobIdRef = useRef<string | null>(null);

  useEffect(() => {
    if (!job || !activeJobId) return;
    const isTerminal = job.status === "completed" || job.status === "failed";
    if (isTerminal && settledJobIdRef.current !== activeJobId) {
      // Only fires once per job (guarded by the ref) when the poll first observes a terminal
      // state, refreshing the views the pipeline would have changed.
      settledJobIdRef.current = activeJobId;
      queryClient.invalidateQueries({ queryKey: ["company", companyId] });
      queryClient.invalidateQueries({ queryKey: ["company-evidence", companyId] });
      queryClient.invalidateQueries({ queryKey: ["company-sources", companyId] });
    }
  }, [job, activeJobId, companyId, queryClient]);

  const runResearch = async () => {
    setActionError(null);
    try {
      const newJob = await startCompanyResearch(companyId);
      setActiveJobId(newJob.id);
    } catch (error) {
      setActionError(extractApiErrorMessage(error, "Could not start research"));
    }
  };

  const addSource = async () => {
    if (!newSourceUrl.trim()) return;
    setActionError(null);
    try {
      await addCompanySource(companyId, { url: newSourceUrl.trim() });
      setNewSourceUrl("");
      queryClient.invalidateQueries({ queryKey: ["company-sources", companyId] });
    } catch (error) {
      setActionError(extractApiErrorMessage(error, "Could not add source"));
    }
  };

  const removeSource = async (sourceId: string) => {
    setActionError(null);
    try {
      await deleteCompanySource(companyId, sourceId);
      queryClient.invalidateQueries({ queryKey: ["company-sources", companyId] });
    } catch (error) {
      setActionError(extractApiErrorMessage(error, "Could not remove source"));
    }
  };

  if (companyQuery.isLoading) {
    return (
      <AppShell>
        <p className="text-sm text-slate-500">Loading company…</p>
      </AppShell>
    );
  }

  if (!company) {
    return (
      <AppShell>
        <p className="text-sm text-red-600">Company not found.</p>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="mb-6 flex items-start justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">{company.name}</h1>
          <p className="text-sm text-slate-500">
            {company.domain} · {company.industry || "Unknown industry"}
          </p>
        </div>
        <div className="flex gap-2">
          {canResearch && (
            <Button
              variant="secondary"
              onClick={runResearch}
              disabled={Boolean(job && JOB_STATUS_ACTIVE.includes(job.status))}
            >
              {job && JOB_STATUS_ACTIVE.includes(job.status) ? "Researching…" : "Run research"}
            </Button>
          )}
          {canEdit && (
            <Link href={`/companies/${companyId}/edit`}>
              <Button variant="secondary">Edit</Button>
            </Link>
          )}
          {canDelete && (
            <Button
              variant="destructive"
              onClick={async () => {
                setActionError(null);
                try {
                  await deleteCompany(companyId);
                  router.push("/companies");
                } catch (error) {
                  setActionError(extractApiErrorMessage(error, "Could not delete company"));
                }
              }}
            >
              Delete
            </Button>
          )}
        </div>
      </div>

      {actionError && (
        <p role="alert" className="mb-4 text-sm text-red-600">
          {actionError}
        </p>
      )}

      {job && (
        <Card className="mb-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-slate-800">
                Research job <StatusBadge value={job.status} />
              </p>
              <p className="mt-1 text-sm text-slate-500">
                {job.current_step || "Queued"}
                {JOB_STATUS_ACTIVE.includes(job.status) ? ` (${job.progress_percentage}%)` : ""}
              </p>
              {job.status === "failed" && (
                <p className="mt-1 text-sm text-red-600">{job.error_message}</p>
              )}
            </div>
          </div>
        </Card>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="flex flex-col gap-4 lg:col-span-2">
          <Card>
            <div className="mb-2 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-slate-900">Overview</h2>
              <StatusBadge value={company.research_status} />
            </div>
            {company.business_description && (
              <p className="text-sm text-slate-700">{company.business_description}</p>
            )}
            <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
              <div>
                <dt className="text-slate-500">Company size</dt>
                <dd className="text-slate-800">{company.company_size || "—"}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Revenue range</dt>
                <dd className="text-slate-800">{company.revenue_range || "—"}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Confidence score</dt>
                <dd className="text-slate-800">{company.confidence_score}/100</dd>
              </div>
              <div>
                <dt className="text-slate-500">Website</dt>
                <dd className="truncate text-slate-800">
                  <a
                    href={company.website}
                    target="_blank"
                    rel="noreferrer"
                    className="text-brand-700 hover:underline"
                  >
                    {company.website}
                  </a>
                </dd>
              </div>
            </dl>
          </Card>

          <Card>
            <h2 className="mb-3 text-lg font-semibold text-slate-900">Research signals</h2>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <TagList label="Locations" values={company.locations} />
              <TagList label="Technology stack" values={company.technology_stack} />
              <TagList label="Business challenges" values={company.business_challenges} />
              <TagList label="Public signals" values={company.public_signals} />
            </div>
            {company.locations.length === 0 &&
              company.technology_stack.length === 0 &&
              company.business_challenges.length === 0 &&
              company.public_signals.length === 0 && (
                <p className="text-sm text-slate-500">
                  No research signals recorded yet — this company hasn&apos;t been through the
                  research pipeline.
                </p>
              )}
          </Card>

          <Card>
            <h2 className="mb-1 text-lg font-semibold text-slate-900">Evidence</h2>
            <p className="mb-3 text-sm text-slate-500">
              Every claim below is AI-generated from a specific source — verify before treating
              it as fact (spec §14/§15).
            </p>
            {evidenceQuery.data?.length ? (
              <ul className="flex flex-col gap-3">
                {evidenceQuery.data.map((item) => (
                  <li key={item.id} className="border-b border-slate-100 pb-3 last:border-0">
                    <div className="flex items-center gap-2 text-xs text-slate-500">
                      <span className="rounded-full bg-slate-100 px-2 py-0.5 capitalize">
                        {item.category.replace(/_/g, " ")}
                      </span>
                      <span>Confidence {item.confidence}/100</span>
                      {item.is_ai_generated && <span>· AI-generated</span>}
                    </div>
                    <p className="mt-1 text-sm text-slate-800">{item.fact_text}</p>
                    <a
                      href={item.source_url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-xs text-brand-700 hover:underline"
                    >
                      {item.source_title || item.source_url}
                    </a>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-slate-500">
                No evidence yet — run research to collect source-backed findings.
              </p>
            )}
          </Card>

          <Card>
            <div className="mb-2 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-slate-900">Contacts</h2>
              {canCreateContact && (
                <Link href={`/contacts/new?company_id=${companyId}`}>
                  <Button variant="secondary">Add contact</Button>
                </Link>
              )}
            </div>
            {contactsQuery.data?.items.length ? (
              <ul className="flex flex-col gap-2">
                {contactsQuery.data.items.map((contact) => (
                  <li key={contact.id} className="flex items-center justify-between text-sm">
                    <Link
                      href={`/contacts/${contact.id}`}
                      className="font-medium text-brand-700 hover:underline"
                    >
                      {contact.full_name}
                    </Link>
                    <span className="text-slate-500">{contact.job_title}</span>
                    <StatusBadge value={contact.verification_status} />
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-slate-500">No contacts linked to this company yet.</p>
            )}
          </Card>
        </div>

        <div className="flex flex-col gap-4">
          <Card>
            <h2 className="mb-2 text-lg font-semibold text-slate-900">Sources</h2>
            {canEdit && (
              <div className="mb-3 flex gap-2">
                <Input
                  placeholder="https://..."
                  value={newSourceUrl}
                  onChange={(e) => setNewSourceUrl(e.target.value)}
                />
                <Button variant="secondary" onClick={addSource}>
                  Add
                </Button>
              </div>
            )}
            {sourcesQuery.data?.length ? (
              <ul className="flex flex-col gap-2">
                {sourcesQuery.data.map((source) => (
                  <li key={source.id} className="flex items-start justify-between gap-2 text-sm">
                    <a
                      href={source.url}
                      target="_blank"
                      rel="noreferrer"
                      className="truncate text-brand-700 hover:underline"
                    >
                      {source.title || source.url}
                    </a>
                    {canEdit && (
                      <button
                        onClick={() => removeSource(source.id)}
                        className="shrink-0 text-slate-400 hover:text-red-600"
                        aria-label="Remove source"
                      >
                        ×
                      </button>
                    )}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-slate-500">No sources recorded yet.</p>
            )}
          </Card>
        </div>
      </div>
    </AppShell>
  );
}

export default function CompanyDetailPage() {
  return (
    <ProtectedRoute>
      <CompanyDetailContent />
    </ProtectedRoute>
  );
}
