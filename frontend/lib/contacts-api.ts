import { api } from "@/lib/api";
import type { Contact, ContactFormValues, ContactListItem, ContactSource } from "@/types/contact";
import type { ApiSuccess } from "@/types/auth";
import type { PaginatedData } from "@/types/product";

export interface ContactListParams {
  search?: string;
  company_id?: string;
  verification_status?: string;
  page?: number;
  page_size?: number;
}

export async function listContacts(
  params: ContactListParams,
): Promise<PaginatedData<ContactListItem>> {
  const res = await api.get<ApiSuccess<PaginatedData<ContactListItem>>>("/contacts", { params });
  return res.data.data;
}

export async function getContact(id: string): Promise<Contact> {
  const res = await api.get<ApiSuccess<Contact>>(`/contacts/${id}`);
  return res.data.data;
}

export async function createContact(values: ContactFormValues): Promise<Contact> {
  const res = await api.post<ApiSuccess<Contact>>("/contacts", values);
  return res.data.data;
}

export async function updateContact(
  id: string,
  values: Partial<ContactFormValues>,
): Promise<Contact> {
  const res = await api.patch<ApiSuccess<Contact>>(`/contacts/${id}`, values);
  return res.data.data;
}

export async function deleteContact(id: string): Promise<void> {
  await api.delete(`/contacts/${id}`);
}

export async function verifyContact(id: string): Promise<Contact> {
  const res = await api.post<ApiSuccess<Contact>>(`/contacts/${id}/verify`);
  return res.data.data;
}

export async function listContactSources(contactId: string): Promise<ContactSource[]> {
  const res = await api.get<ApiSuccess<ContactSource[]>>(`/contacts/${contactId}/sources`);
  return res.data.data;
}

export async function addContactSource(
  contactId: string,
  body: { url: string; title?: string; source_type?: string },
): Promise<ContactSource> {
  const res = await api.post<ApiSuccess<ContactSource>>(`/contacts/${contactId}/sources`, body);
  return res.data.data;
}

export async function deleteContactSource(contactId: string, sourceId: string): Promise<void> {
  await api.delete(`/contacts/${contactId}/sources/${sourceId}`);
}
