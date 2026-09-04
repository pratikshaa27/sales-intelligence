import { api } from "@/lib/api";
import type { ApiSuccess } from "@/types/auth";
import type { PaginatedData } from "@/types/product";
import type {
  CreateLeadValues,
  ExportLeadsRequest,
  Lead,
  LeadActivity,
  LeadListItem,
  LeadNote,
  LeadScore,
  LeadStatus,
  LeadPriority,
  ProductMatchSuggestion,
  SalesBrief,
} from "@/types/lead";

export interface LeadListParams {
  search?: string;
  status?: LeadStatus;
  priority?: LeadPriority;
  product_id?: string;
  company_id?: string;
  assigned_to?: string;
  min_score?: number;
  page?: number;
  page_size?: number;
}

export async function listLeads(params: LeadListParams): Promise<PaginatedData<LeadListItem>> {
  const res = await api.get<ApiSuccess<PaginatedData<LeadListItem>>>("/leads", { params });
  return res.data.data;
}

export async function getLead(id: string): Promise<Lead> {
  const res = await api.get<ApiSuccess<Lead>>(`/leads/${id}`);
  return res.data.data;
}

export async function createLead(values: CreateLeadValues): Promise<Lead> {
  const res = await api.post<ApiSuccess<Lead>>("/leads", values);
  return res.data.data;
}

export async function updateLead(
  id: string,
  values: Partial<{
    name: string;
    contact_id: string | null;
    next_action: string;
    tags: string[];
    priority: LeadPriority;
  }>,
): Promise<Lead> {
  const res = await api.patch<ApiSuccess<Lead>>(`/leads/${id}`, values);
  return res.data.data;
}

export async function deleteLead(id: string): Promise<void> {
  await api.delete(`/leads/${id}`);
}

export async function recalculateScore(id: string): Promise<Lead> {
  const res = await api.post<ApiSuccess<Lead>>(`/leads/${id}/recalculate-score`);
  return res.data.data;
}

export async function listLeadScores(id: string): Promise<LeadScore[]> {
  const res = await api.get<ApiSuccess<LeadScore[]>>(`/leads/${id}/scores`);
  return res.data.data;
}

export async function changeLeadStatus(
  id: string,
  status: LeadStatus,
  reason?: string,
): Promise<Lead> {
  const res = await api.post<ApiSuccess<Lead>>(`/leads/${id}/status`, { status, reason });
  return res.data.data;
}

export async function assignLead(id: string, assignedTo: string | null): Promise<Lead> {
  const res = await api.post<ApiSuccess<Lead>>(`/leads/${id}/assign`, {
    assigned_to: assignedTo,
  });
  return res.data.data;
}

export async function generateBrief(id: string): Promise<SalesBrief> {
  const res = await api.post<ApiSuccess<SalesBrief>>(`/leads/${id}/brief`);
  return res.data.data;
}

export async function listBriefs(id: string): Promise<SalesBrief[]> {
  const res = await api.get<ApiSuccess<SalesBrief[]>>(`/leads/${id}/briefs`);
  return res.data.data;
}

export async function listNotes(id: string): Promise<LeadNote[]> {
  const res = await api.get<ApiSuccess<LeadNote[]>>(`/leads/${id}/notes`);
  return res.data.data;
}

export async function addNote(id: string, body: string): Promise<LeadNote> {
  const res = await api.post<ApiSuccess<LeadNote>>(`/leads/${id}/notes`, { body });
  return res.data.data;
}

export async function listActivities(id: string): Promise<LeadActivity[]> {
  const res = await api.get<ApiSuccess<LeadActivity[]>>(`/leads/${id}/activities`);
  return res.data.data;
}

export async function suggestProductMatches(companyId: string): Promise<ProductMatchSuggestion[]> {
  const res = await api.get<ApiSuccess<ProductMatchSuggestion[]>>("/leads/product-matches", {
    params: { company_id: companyId },
  });
  return res.data.data;
}

export async function exportLeads(body: ExportLeadsRequest): Promise<void> {
  const res = await api.post("/leads/export", body, { responseType: "blob" });
  const disposition = res.headers["content-disposition"] as string | undefined;
  const match = disposition?.match(/filename="?([^"]+)"?/);
  const filename = match?.[1] ?? "leads_export";

  const url = window.URL.createObjectURL(res.data as Blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}
