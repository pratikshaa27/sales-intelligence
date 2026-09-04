export interface LeadsByStatusItem {
  status: string;
  count: number;
}

export interface LeadsByProductItem {
  product_id: string;
  product_name: string;
  count: number;
}

export interface LeadsByIndustryItem {
  industry: string;
  count: number;
}

export interface TeamPerformanceItem {
  user_id: string;
  full_name: string;
  assigned_count: number;
  won_count: number;
  lost_count: number;
  win_rate: number;
  average_score: number;
}

export interface RecentActivityItem {
  lead_id: string;
  lead_name: string;
  activity_type: string;
  description: string;
  created_at: string;
}

export interface DashboardSummary {
  scope: "organization" | "me";
  total_leads: number;
  new_leads: number;
  assigned_leads: number;
  contacted_leads: number;
  won_leads: number;
  lost_leads: number;
  high_priority_leads: number;
  average_lead_score: number;
  total_companies_researched: number;
  research_jobs_running: number;
  research_jobs_completed: number;
  leads_by_status: LeadsByStatusItem[];
  leads_by_product: LeadsByProductItem[];
  leads_by_industry: LeadsByIndustryItem[];
  team_performance: TeamPerformanceItem[];
  recent_activities: RecentActivityItem[];
}

export interface LeadsFunnelItem {
  status: string;
  count: number;
}

export interface LeadsAnalytics {
  scope: "organization" | "me";
  funnel: LeadsFunnelItem[];
  total_won: number;
  total_lost: number;
  win_rate: number;
  average_score_by_priority: Record<string, number>;
}

export interface ProductPerformanceItem {
  product_id: string;
  product_name: string;
  lead_count: number;
  average_score: number;
  won_count: number;
  win_rate: number;
}

export interface ProductsAnalytics {
  products: ProductPerformanceItem[];
}

export interface TeamAnalytics {
  team: TeamPerformanceItem[];
}
