"use client";

import { useQuery } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";

import { AppShell } from "@/components/layout/app-shell";
import { CompanyForm } from "@/components/forms/company-form";
import { ProtectedRoute } from "@/components/shared/protected-route";
import { getCompany, updateCompany } from "@/lib/companies-api";
import type { CompanyFormSchemaValues } from "@/lib/validations";

function EditCompanyContent() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const companyId = params.id;

  const { data: company, isLoading } = useQuery({
    queryKey: ["company", companyId],
    queryFn: () => getCompany(companyId),
  });

  const onSubmit = async (values: CompanyFormSchemaValues) => {
    await updateCompany(companyId, values);
    router.push(`/companies/${companyId}`);
  };

  return (
    <AppShell>
      <h1 className="mb-6 text-xl font-semibold text-slate-900">Edit company</h1>
      {isLoading && <p className="text-sm text-slate-500">Loading…</p>}
      {company && (
        <CompanyForm defaultValues={company} submitLabel="Save changes" onSubmit={onSubmit} />
      )}
    </AppShell>
  );
}

export default function EditCompanyPage() {
  return (
    <ProtectedRoute>
      <EditCompanyContent />
    </ProtectedRoute>
  );
}
