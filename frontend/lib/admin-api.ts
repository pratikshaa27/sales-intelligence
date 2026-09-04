import { api } from "@/lib/api";
import type { ApiSuccess } from "@/types/auth";
import type { PaginatedData } from "@/types/product";
import type { AuditLogEntry } from "@/types/admin";

export interface AuditLogListParams {
  action?: string;
  page?: number;
  page_size?: number;
}

export async function listAuditLogs(
  params: AuditLogListParams,
): Promise<PaginatedData<AuditLogEntry>> {
  const res = await api.get<ApiSuccess<PaginatedData<AuditLogEntry>>>("/admin/audit-logs", {
    params,
  });
  return res.data.data;
}
