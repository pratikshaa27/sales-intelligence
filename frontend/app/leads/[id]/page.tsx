"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";

import { AppShell } from "@/components/layout/app-shell";
import { ProtectedRoute } from "@/components/shared/protected-route";
import { StatusBadge } from "@/components/shared/status-badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { useAuth } from "@/hooks/use-auth";
import { extractApiErrorMessage } from "@/lib/api";
import { getCompany } from "@/lib/companies-api";
import { getContact } from "@/lib/contacts-api";
import {
  addNote,
  assignLead,
  changeLeadStatus,
  deleteLead,
  generateBrief,
  getLead,
  listActivities,
  listBriefs,
  listLeadScores,
  listNotes,
  recalculateScore,
} from "@/lib/leads-api";
import { listMembers } from "@/lib/organizations-api";
import { hasPermission } from "@/lib/permissions";
import { getProduct } from "@/lib/products-api";
import { LEAD_STATUSES, type LeadStatus } from "@/types/lead";

function ScoreBar({ label, value, max }: { label: string; value: number; max: number }) {
  const pct = max > 0 ? Math.round((value / max) * 100) : 0;
  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-xs text-slate-600">
        <span>{label}</span>
        <span>
          {value}/{max}
        </span>
      </div>
      <div className="h-2 rounded-full bg-slate-100">
        <div className="h-2 rounded-full bg-brand-600" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function LeadDetailContent() {
  const { me } = useAuth();
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const leadId = params.id;
  const queryClient = useQueryClient();
  const [actionError, setActionError] = useState<string | null>(null);
  const [statusReason, setStatusReason] = useState("");
  const [noteBody, setNoteBody] = useState("");

  const leadQuery = useQuery({ queryKey: ["lead", leadId], queryFn: () => getLead(leadId) });
  const lead = leadQuery.data;

  const companyQuery = useQuery({
    queryKey: ["company", lead?.company_id],
    queryFn: () => getCompany(lead!.company_id),
    enabled: Boolean(lead),
  });
  const productQuery = useQuery({
    queryKey: ["product", lead?.product_id],
    queryFn: () => getProduct(lead!.product_id),
    enabled: Boolean(lead),
  });
  const contactQuery = useQuery({
    queryKey: ["contact", lead?.contact_id],
    queryFn: () => getContact(lead!.contact_id as string),
    enabled: Boolean(lead?.contact_id),
  });
  const scoresQuery = useQuery({
    queryKey: ["lead-scores", leadId],
    queryFn: () => listLeadScores(leadId),
  });
  const briefsQuery = useQuery({
    queryKey: ["lead-briefs", leadId],
    queryFn: () => listBriefs(leadId),
  });
  const notesQuery = useQuery({ queryKey: ["lead-notes", leadId], queryFn: () => listNotes(leadId) });
  const activitiesQuery = useQuery({
    queryKey: ["lead-activities", leadId],
    queryFn: () => listActivities(leadId),
  });
  const membersQuery = useQuery({ queryKey: ["members"], queryFn: listMembers });

  const canEdit = hasPermission(me?.permissions, "leads.edit");
  const canScore = hasPermission(me?.permissions, "leads.score");
  const canBrief = hasPermission(me?.permissions, "leads.brief");
  const canAssign = hasPermission(me?.permissions, "leads.assign");
  const canDelete = hasPermission(me?.permissions, "leads.delete");

  const latestScore = scoresQuery.data?.[0];
  const latestBrief = briefsQuery.data?.[0];

  const invalidateAll = () => {
    queryClient.invalidateQueries({ queryKey: ["lead", leadId] });
    queryClient.invalidateQueries({ queryKey: ["lead-scores", leadId] });
    queryClient.invalidateQueries({ queryKey: ["lead-activities", leadId] });
  };

  const onRecalculate = async () => {
    setActionError(null);
    try {
      await recalculateScore(leadId);
      invalidateAll();
    } catch (error) {
      setActionError(extractApiErrorMessage(error, "Could not recalculate score"));
    }
  };

  const onGenerateBrief = async () => {
    setActionError(null);
    try {
      await generateBrief(leadId);
      queryClient.invalidateQueries({ queryKey: ["lead-briefs", leadId] });
      queryClient.invalidateQueries({ queryKey: ["lead-activities", leadId] });
    } catch (error) {
      setActionError(extractApiErrorMessage(error, "Could not generate sales brief"));
    }
  };

  const onStatusChange = async (status: LeadStatus) => {
    setActionError(null);
    try {
      await changeLeadStatus(leadId, status, statusReason || undefined);
      setStatusReason("");
      invalidateAll();
    } catch (error) {
      setActionError(extractApiErrorMessage(error, "Could not change status"));
    }
  };

  const onAssign = async (userId: string) => {
    setActionError(null);
    try {
      await assignLead(leadId, userId || null);
      invalidateAll();
    } catch (error) {
      setActionError(extractApiErrorMessage(error, "Could not update assignment"));
    }
  };

  const onAddNote = async () => {
    if (!noteBody.trim()) return;
    setActionError(null);
    try {
      await addNote(leadId, noteBody.trim());
      setNoteBody("");
      queryClient.invalidateQueries({ queryKey: ["lead-notes", leadId] });
      queryClient.invalidateQueries({ queryKey: ["lead-activities", leadId] });
    } catch (error) {
      setActionError(extractApiErrorMessage(error, "Could not add note"));
    }
  };

  const onDelete = async () => {
    setActionError(null);
    try {
      await deleteLead(leadId);
      router.push("/leads");
    } catch (error) {
      setActionError(extractApiErrorMessage(error, "Could not delete lead"));
    }
  };

  if (leadQuery.isLoading) {
    return (
      <AppShell>
        <p className="text-sm text-slate-500">Loading lead…</p>
      </AppShell>
    );
  }

  if (!lead) {
    return (
      <AppShell>
        <p className="text-sm text-red-600">Lead not found.</p>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="mb-6 flex items-start justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">{lead.name}</h1>
          <p className="text-sm text-slate-500">
            {companyQuery.data?.name ?? "…"} · {productQuery.data?.name ?? "…"}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <StatusBadge value={lead.priority} />
          <StatusBadge value={lead.status} />
          {canDelete && (
            <Button variant="destructive" onClick={onDelete}>
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

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="flex flex-col gap-4 lg:col-span-2">
          <Card>
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-slate-900">
                Lead score — {lead.total_score}/100
              </h2>
              {canScore && (
                <Button variant="secondary" onClick={onRecalculate}>
                  Recalculate
                </Button>
              )}
            </div>
            <p className="mb-3 text-xs text-slate-500">
              Every point below is rule-based and explainable — this is never an opaque AI number.
            </p>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <ScoreBar label="Fit" value={lead.fit_score} max={30} />
              <ScoreBar label="Need" value={lead.need_score} max={25} />
              <ScoreBar label="Authority" value={lead.authority_score} max={15} />
              <ScoreBar label="Timing" value={lead.timing_score} max={15} />
              <ScoreBar label="Data confidence" value={lead.data_confidence_score} max={15} />
            </div>
            {latestScore && (
              <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div>
                  <p className="text-sm font-medium text-slate-700">Why this score</p>
                  <ul className="mt-1 list-inside list-disc text-sm text-slate-600">
                    {latestScore.reasons.map((r, i) => (
                      <li key={i}>{r}</li>
                    ))}
                  </ul>
                </div>
                {latestScore.missing_information.length > 0 && (
                  <div>
                    <p className="text-sm font-medium text-slate-700">Missing information</p>
                    <ul className="mt-1 list-inside list-disc text-sm text-slate-500">
                      {latestScore.missing_information.map((m, i) => (
                        <li key={i}>{m}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </Card>

          <Card>
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-slate-900">Sales brief</h2>
              {canBrief && (
                <Button variant="secondary" onClick={onGenerateBrief}>
                  {latestBrief ? "Regenerate" : "Generate brief"}
                </Button>
              )}
            </div>
            {latestBrief ? (
              <div className="flex flex-col gap-3 text-sm text-slate-700">
                <p className="rounded-md bg-amber-50 p-2 text-xs text-amber-800">
                  {latestBrief.disclaimer}
                </p>
                {latestBrief.company_overview && <p>{latestBrief.company_overview}</p>}
                {latestBrief.possible_business_problem && (
                  <div>
                    <p className="font-medium text-slate-800">Possible business problem</p>
                    <p>{latestBrief.possible_business_problem}</p>
                  </div>
                )}
                <div>
                  <p className="font-medium text-slate-800">Suggested opener (AI-drafted)</p>
                  <p>{latestBrief.suggested_opener}</p>
                </div>
                <div>
                  <p className="font-medium text-slate-800">Discovery questions (AI-drafted)</p>
                  <ul className="list-inside list-disc">
                    {latestBrief.discovery_questions.map((q, i) => (
                      <li key={i}>{q}</li>
                    ))}
                  </ul>
                </div>
                <div>
                  <p className="font-medium text-slate-800">Recommended next action</p>
                  <p>{latestBrief.recommended_next_action}</p>
                </div>
                <p className="text-xs text-slate-400">Generated by: {latestBrief.ai_provider}</p>
              </div>
            ) : (
              <p className="text-sm text-slate-500">
                No brief generated yet — generate one to get a suggested opener and discovery
                questions.
              </p>
            )}
          </Card>

          <Card>
            <h2 className="mb-3 text-lg font-semibold text-slate-900">Notes</h2>
            {canEdit && (
              <div className="mb-3 flex flex-col gap-2">
                <Textarea
                  placeholder="Add a note about this lead…"
                  value={noteBody}
                  onChange={(e) => setNoteBody(e.target.value)}
                />
                <Button variant="secondary" onClick={onAddNote} className="self-start">
                  Add note
                </Button>
              </div>
            )}
            {notesQuery.data?.length ? (
              <ul className="flex flex-col gap-2">
                {notesQuery.data.map((note) => (
                  <li key={note.id} className="border-b border-slate-100 pb-2 text-sm last:border-0">
                    <p className="text-slate-800">{note.body}</p>
                    <p className="text-xs text-slate-400">
                      {new Date(note.created_at).toLocaleString()}
                    </p>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-slate-500">No notes yet.</p>
            )}
          </Card>

          <Card>
            <h2 className="mb-3 text-lg font-semibold text-slate-900">Activity</h2>
            {activitiesQuery.data?.length ? (
              <ul className="flex flex-col gap-2">
                {activitiesQuery.data.map((activity) => (
                  <li key={activity.id} className="text-sm">
                    <span className="text-slate-800">{activity.description}</span>{" "}
                    <span className="text-xs text-slate-400">
                      {new Date(activity.created_at).toLocaleString()}
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-slate-500">No activity recorded yet.</p>
            )}
          </Card>
        </div>

        <div className="flex flex-col gap-4">
          <Card>
            <h2 className="mb-3 text-lg font-semibold text-slate-900">Status</h2>
            {canEdit ? (
              <div className="flex flex-col gap-2">
                <Select
                  value={lead.status}
                  onChange={(e) => onStatusChange(e.target.value as LeadStatus)}
                >
                  {LEAD_STATUSES.map((s) => (
                    <option key={s} value={s}>
                      {s.replace(/_/g, " ")}
                    </option>
                  ))}
                </Select>
                <Textarea
                  placeholder="Reason for status change (optional)"
                  value={statusReason}
                  onChange={(e) => setStatusReason(e.target.value)}
                  rows={2}
                />
              </div>
            ) : (
              <StatusBadge value={lead.status} />
            )}
          </Card>

          <Card>
            <h2 className="mb-3 text-lg font-semibold text-slate-900">Contact</h2>
            {lead.contact_id ? (
              contactQuery.data ? (
                <dl className="grid grid-cols-1 gap-2 text-sm">
                  <div>
                    <dt className="text-slate-500">Name</dt>
                    <dd className="text-slate-800">{contactQuery.data.full_name}</dd>
                  </div>
                  {contactQuery.data.job_title && (
                    <div>
                      <dt className="text-slate-500">Job title</dt>
                      <dd className="text-slate-800">{contactQuery.data.job_title}</dd>
                    </div>
                  )}
                  <div>
                    <dt className="text-slate-500">Email</dt>
                    <dd className="text-slate-800">
                      {contactQuery.data.business_email || "Not on file"}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-slate-500">Phone</dt>
                    <dd className="text-slate-800">
                      {contactQuery.data.business_phone || "Not on file"}
                    </dd>
                  </div>
                </dl>
              ) : (
                <p className="text-sm text-slate-500">Loading contact…</p>
              )
            ) : (
              <p className="text-sm text-slate-500">
                No contact linked to this lead yet — edit the lead to add one.
              </p>
            )}
          </Card>

          <Card>
            <h2 className="mb-3 text-lg font-semibold text-slate-900">Assignment</h2>
            {canAssign ? (
              <Select
                value={lead.assigned_to ?? ""}
                onChange={(e) => onAssign(e.target.value)}
              >
                <option value="">Unassigned</option>
                {membersQuery.data?.map((m) => (
                  <option key={m.user_id} value={m.user_id}>
                    {m.full_name}
                  </option>
                ))}
              </Select>
            ) : (
              <p className="text-sm text-slate-600">
                {membersQuery.data?.find((m) => m.user_id === lead.assigned_to)?.full_name ??
                  "Unassigned"}
              </p>
            )}
          </Card>

          <Card>
            <h2 className="mb-2 text-lg font-semibold text-slate-900">Details</h2>
            <dl className="grid grid-cols-1 gap-2 text-sm">
              <div>
                <dt className="text-slate-500">Source</dt>
                <dd className="text-slate-800">{lead.source}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Created</dt>
                <dd className="text-slate-800">{new Date(lead.created_at).toLocaleString()}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Last activity</dt>
                <dd className="text-slate-800">
                  {new Date(lead.last_activity_at).toLocaleString()}
                </dd>
              </div>
            </dl>
          </Card>
        </div>
      </div>
    </AppShell>
  );
}

export default function LeadDetailPage() {
  return (
    <ProtectedRoute>
      <LeadDetailContent />
    </ProtectedRoute>
  );
}
