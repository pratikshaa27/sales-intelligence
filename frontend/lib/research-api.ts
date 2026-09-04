import { api } from "@/lib/api";
import type { ApiSuccess } from "@/types/auth";
import type { PaginatedData } from "@/types/product";
import type { JobStatus, JobType, ResearchEvidence, ResearchJob } from "@/types/research";

export interface JobListParams {
  job_type?: string;
  status?: string;
  page?: number;
  page_size?: number;
}

export async function listJobs(params: JobListParams): Promise<PaginatedData<ResearchJob>> {
  const res = await api.get<ApiSuccess<PaginatedData<ResearchJob>>>("/jobs", { params });
  return res.data.data;
}

export async function getJob(id: string): Promise<ResearchJob> {
  const res = await api.get<ApiSuccess<ResearchJob>>(`/jobs/${id}`);
  return res.data.data;
}

export async function cancelJob(id: string): Promise<ResearchJob> {
  const res = await api.post<ApiSuccess<ResearchJob>>(`/jobs/${id}/cancel`);
  return res.data.data;
}

export async function startCompanyResearch(companyId: string): Promise<ResearchJob> {
  const res = await api.post<ApiSuccess<ResearchJob>>(`/companies/${companyId}/research`);
  return res.data.data;
}

export interface DiscoverCompaniesParams {
  industry?: string;
  location?: string;
  company_size?: string;
  keywords?: string[];
  number_of_companies?: number;
}

export async function discoverCompanies(body: DiscoverCompaniesParams): Promise<ResearchJob> {
  const res = await api.post<ApiSuccess<ResearchJob>>("/companies/discover", body);
  return res.data.data;
}

export async function listCompanyEvidence(companyId: string): Promise<ResearchEvidence[]> {
  const res = await api.get<ApiSuccess<ResearchEvidence[]>>(`/companies/${companyId}/evidence`);
  return res.data.data;
}

export const JOB_TYPE_LABELS: Record<JobType, string> = {
  company_research: "Company research",
  company_discovery: "Company discovery",
};

export const JOB_STATUS_ACTIVE: JobStatus[] = ["queued", "running"];
