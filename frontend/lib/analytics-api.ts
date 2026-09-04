import { api } from "@/lib/api";
import type { ApiSuccess } from "@/types/auth";
import type {
  DashboardSummary,
  LeadsAnalytics,
  ProductsAnalytics,
  TeamAnalytics,
} from "@/types/analytics";

export async function getDashboard(): Promise<DashboardSummary> {
  const res = await api.get<ApiSuccess<DashboardSummary>>("/analytics/dashboard");
  return res.data.data;
}

export async function getLeadsAnalytics(): Promise<LeadsAnalytics> {
  const res = await api.get<ApiSuccess<LeadsAnalytics>>("/analytics/leads");
  return res.data.data;
}

export async function getProductsAnalytics(): Promise<ProductsAnalytics> {
  const res = await api.get<ApiSuccess<ProductsAnalytics>>("/analytics/products");
  return res.data.data;
}

export async function getTeamAnalytics(): Promise<TeamAnalytics> {
  const res = await api.get<ApiSuccess<TeamAnalytics>>("/analytics/team");
  return res.data.data;
}
