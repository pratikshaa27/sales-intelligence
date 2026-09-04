"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense } from "react";

import { AppShell } from "@/components/layout/app-shell";
import { ContactForm } from "@/components/forms/contact-form";
import { ProtectedRoute } from "@/components/shared/protected-route";
import { createContact } from "@/lib/contacts-api";
import type { ContactFormSchemaValues } from "@/lib/validations";

function NewContactForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const companyId = searchParams.get("company_id") ?? undefined;

  const onSubmit = async (values: ContactFormSchemaValues) => {
    const contact = await createContact(values);
    router.push(`/contacts/${contact.id}`);
  };

  return (
    <ContactForm
      defaultValues={companyId ? { company_id: companyId } : undefined}
      lockCompany={Boolean(companyId)}
      submitLabel="Create contact"
      onSubmit={onSubmit}
    />
  );
}

function NewContactContent() {
  return (
    <AppShell>
      <h1 className="mb-6 text-xl font-semibold text-slate-900">New contact</h1>
      <Suspense fallback={<p className="text-sm text-slate-500">Loading…</p>}>
        <NewContactForm />
      </Suspense>
    </AppShell>
  );
}

export default function NewContactPage() {
  return (
    <ProtectedRoute>
      <NewContactContent />
    </ProtectedRoute>
  );
}
