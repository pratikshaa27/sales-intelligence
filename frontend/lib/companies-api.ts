import { api } from "@/lib/api";
import type { Company, CompanyFormValues, CompanyListItem, CompanySource } from "@/types/company";
import type { ApiSuccess } from "@/types/auth";
import type { PaginatedData } from "@/types/product";

export interface CompanyListParams {
  search?: string;
  industry?: string;
  company_size?: string;
  min_confidence?: number;
  research_status?: string;
  page?: number;
  page_size?: number;
}

export async function listCompanies(
  params: CompanyListParams,
): Promise<PaginatedData<CompanyListItem>> {
  const res = await api.get<ApiSuccess<PaginatedData<CompanyListItem>>>("/companies", { params });
  return res.data.data;
}

export async function getCompany(id: string): Promise<Company> {
  const res = await api.get<ApiSuccess<Company>>(`/companies/${id}`);
  return res.data.data;
}

export async function createCompany(values: CompanyFormValues): Promise<Company> {
  const res = await api.post<ApiSuccess<Company>>("/companies", values);
  return res.data.data;
}

export async function updateCompany(
  id: string,
  values: Partial<CompanyFormValues>,
): Promise<Company> {
  const res = await api.patch<ApiSuccess<Company>>(`/companies/${id}`, values);
  return res.data.data;
}

export async function deleteCompany(id: string): Promise<void> {
  await api.delete(`/companies/${id}`);
}

export async function listCompanySources(companyId: string): Promise<CompanySource[]> {
  const res = await api.get<ApiSuccess<CompanySource[]>>(`/companies/${companyId}/sources`);
  return res.data.data;
}

export async function addCompanySource(
  companyId: string,
  body: { url: string; title?: string; source_type?: string },
): Promise<CompanySource> {
  const res = await api.post<ApiSuccess<CompanySource>>(`/companies/${companyId}/sources`, body);
  return res.data.data;
}

export async function deleteCompanySource(companyId: string, sourceId: string): Promise<void> {
  await api.delete(`/companies/${companyId}/sources/${sourceId}`);
}
