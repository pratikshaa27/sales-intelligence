import { api } from "@/lib/api";
import type { ApiSuccess } from "@/types/auth";
import type { ImportEntityType, ImportJob, ImportJobStatus, ImportPreview } from "@/types/import";
import type { PaginatedData } from "@/types/product";

const MULTIPART_HEADERS = { "Content-Type": "multipart/form-data" };

export async function previewImport(
  entityType: ImportEntityType,
  file: File,
): Promise<ImportPreview> {
  const formData = new FormData();
  formData.append("file", file);
  const res = await api.post<ApiSuccess<ImportPreview>>(
    `/imports/${entityType}/preview`,
    formData,
    { headers: MULTIPART_HEADERS },
  );
  return res.data.data;
}

export async function startImport(entityType: ImportEntityType, file: File): Promise<ImportJob> {
  const formData = new FormData();
  formData.append("file", file);
  const res = await api.post<ApiSuccess<ImportJob>>(`/imports/${entityType}`, formData, {
    headers: MULTIPART_HEADERS,
  });
  return res.data.data;
}

export interface ImportListParams {
  entity_type?: ImportEntityType;
  status?: ImportJobStatus;
  page?: number;
  page_size?: number;
}

export async function listImports(params: ImportListParams): Promise<PaginatedData<ImportJob>> {
  const res = await api.get<ApiSuccess<PaginatedData<ImportJob>>>("/imports", { params });
  return res.data.data;
}

export async function getImport(id: string): Promise<ImportJob> {
  const res = await api.get<ApiSuccess<ImportJob>>(`/imports/${id}`);
  return res.data.data;
}

export async function cancelImport(id: string): Promise<ImportJob> {
  const res = await api.post<ApiSuccess<ImportJob>>(`/imports/${id}/cancel`);
  return res.data.data;
}
