"use client";

import { useQuery } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";

import { AppShell } from "@/components/layout/app-shell";
import { ContactForm } from "@/components/forms/contact-form";
import { ProtectedRoute } from "@/components/shared/protected-route";
import { getContact, updateContact } from "@/lib/contacts-api";
import type { ContactFormSchemaValues } from "@/lib/validations";

function EditContactContent() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const contactId = params.id;

  const { data: contact, isLoading } = useQuery({
    queryKey: ["contact", contactId],
    queryFn: () => getContact(contactId),
  });

  const onSubmit = async (values: ContactFormSchemaValues) => {
    await updateContact(contactId, values);
    router.push(`/contacts/${contactId}`);
  };

  return (
    <AppShell>
      <h1 className="mb-6 text-xl font-semibold text-slate-900">Edit contact</h1>
      {isLoading && <p className="text-sm text-slate-500">Loading…</p>}
      {contact && (
        <ContactForm defaultValues={contact} submitLabel="Save changes" onSubmit={onSubmit} />
      )}
    </AppShell>
  );
}

export default function EditContactPage() {
  return (
    <ProtectedRoute>
      <EditContactContent />
    </ProtectedRoute>
  );
}
