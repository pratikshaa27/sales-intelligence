"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";

import { AppShell } from "@/components/layout/app-shell";
import { ProtectedRoute } from "@/components/shared/protected-route";
import { StatusBadge } from "@/components/shared/status-badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useAuth } from "@/hooks/use-auth";
import { getCompany } from "@/lib/companies-api";
import { extractApiErrorMessage } from "@/lib/api";
import {
  addContactSource,
  deleteContact,
  deleteContactSource,
  getContact,
  listContactSources,
  verifyContact,
} from "@/lib/contacts-api";
import { hasPermission } from "@/lib/permissions";

function ContactDetailContent() {
  const { me } = useAuth();
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const contactId = params.id;
  const queryClient = useQueryClient();
  const [actionError, setActionError] = useState<string | null>(null);
  const [newSourceUrl, setNewSourceUrl] = useState("");

  const contactQuery = useQuery({
    queryKey: ["contact", contactId],
    queryFn: () => getContact(contactId),
  });
  const sourcesQuery = useQuery({
    queryKey: ["contact-sources", contactId],
    queryFn: () => listContactSources(contactId),
  });
  const companyQuery = useQuery({
    queryKey: ["company", contactQuery.data?.company_id],
    queryFn: () => getCompany(contactQuery.data!.company_id),
    enabled: Boolean(contactQuery.data?.company_id),
  });

  const canEdit = hasPermission(me?.permissions, "contacts.edit");
  const canDelete = hasPermission(me?.permissions, "contacts.delete");
  const canVerify = hasPermission(me?.permissions, "contacts.verify");

  const contact = contactQuery.data;

  const runAction = async (action: () => Promise<unknown>) => {
    setActionError(null);
    try {
      await action();
      queryClient.invalidateQueries({ queryKey: ["contact", contactId] });
    } catch (error) {
      setActionError(extractApiErrorMessage(error, "Action failed"));
    }
  };

  const addSource = async () => {
    if (!newSourceUrl.trim()) return;
    setActionError(null);
    try {
      await addContactSource(contactId, { url: newSourceUrl.trim() });
      setNewSourceUrl("");
      queryClient.invalidateQueries({ queryKey: ["contact-sources", contactId] });
    } catch (error) {
      setActionError(extractApiErrorMessage(error, "Could not add source"));
    }
  };

  const removeSource = async (sourceId: string) => {
    setActionError(null);
    try {
      await deleteContactSource(contactId, sourceId);
      queryClient.invalidateQueries({ queryKey: ["contact-sources", contactId] });
    } catch (error) {
      setActionError(extractApiErrorMessage(error, "Could not remove source"));
    }
  };

  if (contactQuery.isLoading) {
    return (
      <AppShell>
        <p className="text-sm text-slate-500">Loading contact…</p>
      </AppShell>
    );
  }

  if (!contact) {
    return (
      <AppShell>
        <p className="text-sm text-red-600">Contact not found.</p>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="mb-6 flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-semibold text-slate-900">{contact.full_name}</h1>
            <StatusBadge value={contact.verification_status} />
          </div>
          <p className="text-sm text-slate-500">
            {contact.job_title}
            {companyQuery.data && (
              <>
                {" at "}
                <Link
                  href={`/companies/${companyQuery.data.id}`}
                  className="text-brand-700 hover:underline"
                >
                  {companyQuery.data.name}
                </Link>
              </>
            )}
          </p>
        </div>
        <div className="flex gap-2">
          {canVerify && contact.verification_status !== "verified" && (
            <Button variant="secondary" onClick={() => runAction(() => verifyContact(contactId))}>
              Mark verified
            </Button>
          )}
          {canEdit && (
            <Link href={`/contacts/${contactId}/edit`}>
              <Button variant="secondary">Edit</Button>
            </Link>
          )}
          {canDelete && (
            <Button
              variant="destructive"
              onClick={() =>
                runAction(async () => {
                  await deleteContact(contactId);
                  router.push("/contacts");
                })
              }
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

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="flex flex-col gap-4 lg:col-span-2">
          <Card>
            <h2 className="mb-2 text-lg font-semibold text-slate-900">Details</h2>
            <dl className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <dt className="text-slate-500">Department</dt>
                <dd className="text-slate-800">{contact.department || "—"}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Seniority</dt>
                <dd className="text-slate-800">{contact.seniority || "—"}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Confidence score</dt>
                <dd className="text-slate-800">{contact.confidence_score}/100</dd>
              </div>
              <div>
                <dt className="text-slate-500">Public profile</dt>
                <dd className="truncate text-slate-800">
                  {contact.profile_url ? (
                    <a
                      href={contact.profile_url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-brand-700 hover:underline"
                    >
                      {contact.profile_url}
                    </a>
                  ) : (
                    "—"
                  )}
                </dd>
              </div>
              <div>
                <dt className="text-slate-500">Business email</dt>
                <dd className="text-slate-800">{contact.business_email || "—"}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Business phone</dt>
                <dd className="text-slate-800">{contact.business_phone || "—"}</dd>
              </div>
            </dl>
            {contact.role_relevance && (
              <div className="mt-4">
                <p className="text-sm font-medium text-slate-500">Role relevance</p>
                <p className="mt-1 text-sm text-slate-700">{contact.role_relevance}</p>
              </div>
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

export default function ContactDetailPage() {
  return (
    <ProtectedRoute>
      <ContactDetailContent />
    </ProtectedRoute>
  );
}
