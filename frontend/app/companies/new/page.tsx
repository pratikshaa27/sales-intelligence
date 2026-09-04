"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense } from "react";

import { AppShell } from "@/components/layout/app-shell";
import { CompanyForm } from "@/components/forms/company-form";
import { ProtectedRoute } from "@/components/shared/protected-route";
import { createCompany } from "@/lib/companies-api";
import type { CompanyFormSchemaValues } from "@/lib/validations";

function NewCompanyForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const prefillWebsite = searchParams.get("website") ?? "";
  const prefillName = searchParams.get("name") ?? "";

  const onSubmit = async (values: CompanyFormSchemaValues) => {
    const company = await createCompany(values);
    router.push(`/companies/${company.id}`);
  };

  return (
    <CompanyForm
      defaultValues={{ website: prefillWebsite, name: prefillName }}
      submitLabel="Create company"
      onSubmit={onSubmit}
    />
  );
}

function NewCompanyContent() {
  return (
    <AppShell>
      <h1 className="mb-6 text-xl font-semibold text-slate-900">New company</h1>
      <Suspense fallback={<p className="text-sm text-slate-500">Loading…</p>}>
        <NewCompanyForm />
      </Suspense>
    </AppShell>
  );
}

export default function NewCompanyPage() {
  return (
    <ProtectedRoute>
      <NewCompanyContent />
    </ProtectedRoute>
  );
}
