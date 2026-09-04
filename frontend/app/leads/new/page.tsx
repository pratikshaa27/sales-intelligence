"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense } from "react";

import { AppShell } from "@/components/layout/app-shell";
import { LeadForm } from "@/components/forms/lead-form";
import { ProtectedRoute } from "@/components/shared/protected-route";
import { createLead } from "@/lib/leads-api";
import type { CreateLeadFormValues } from "@/lib/validations";

function NewLeadForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const companyId = searchParams.get("company_id") ?? undefined;

  const onSubmit = async (values: CreateLeadFormValues) => {
    const lead = await createLead({
      company_id: values.company_id,
      product_id: values.product_id,
      contact_id: values.contact_id || null,
      name: values.name,
      source: values.source,
      tags: values.tags,
    });
    router.push(`/leads/${lead.id}`);
  };

  return (
    <LeadForm
      defaultValues={companyId ? { company_id: companyId } : undefined}
      lockCompany={Boolean(companyId)}
      submitLabel="Create lead"
      onSubmit={onSubmit}
    />
  );
}

function NewLeadContent() {
  return (
    <AppShell>
      <h1 className="mb-6 text-xl font-semibold text-slate-900">New lead</h1>
      <Suspense fallback={<p className="text-sm text-slate-500">Loading…</p>}>
        <NewLeadForm />
      </Suspense>
    </AppShell>
  );
}

export default function NewLeadPage() {
  return (
    <ProtectedRoute>
      <NewLeadContent />
    </ProtectedRoute>
  );
}
