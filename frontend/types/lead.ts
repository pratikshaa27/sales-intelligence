export type LeadStatus =
  | "new"
  | "researching"
  | "qualified"
  | "assigned"
  | "contacted"
  | "meeting_scheduled"
  | "proposal_sent"
  | "negotiation"
  | "won"
  | "lost"
  | "disqualified"
  | "archived";

export type LeadPriority = "low" | "medium" | "high" | "critical";

export type ActivityType =
  | "created"
  | "status_changed"
  | "assigned"
  | "note_added"
  | "score_recalculated"
  | "brief_generated"
  | "research_rerun"
  | "other";

export const LEAD_STATUSES: LeadStatus[] = [
  "new",
  "researching",
  "qualified",
  "assigned",
  "contacted",
  "meeting_scheduled",
  "proposal_sent",
  "negotiation",
  "won",
  "lost",
  "disqualified",
  "archived",
];

export interface Lead {
  id: string;
  organization_id: string;
  company_id: string;
  contact_id: string | null;
  product_id: string;
  name: string;
  source: string;
  status: LeadStatus;
  priority: LeadPriority;
  total_score: number;
  fit_score: number;
  need_score: number;
  authority_score: number;
  timing_score: number;
  data_confidence_score: number;
  assigned_to: string | null;
  research_summary: string;
  next_action: string;
  tags: string[];
  last_activity_at: string;
  created_at: string;
  updated_at: string;
}

export interface LeadListItem {
  id: string;
  company_id: string;
  product_id: string;
  name: string;
  status: LeadStatus;
  priority: LeadPriority;
  total_score: number;
  assigned_to: string | null;
  created_at: string;
}

export interface LeadScore {
  id: string;
  total_score: number;
  fit_score: number;
  need_score: number;
  authority_score: number;
  timing_score: number;
  confidence_score: number;
  reasons: string[];
  missing_information: string[];
  created_at: string;
}

export interface SalesBrief {
  id: string;
  company_overview: string;
  why_relevant: string;
  matched_product_summary: string;
  possible_business_problem: string;
  evidence_summary: { category: string; summary: string; source_url: string }[];
  relevant_decision_maker: string;
  suggested_opener: string;
  discovery_questions: string[];
  recommended_next_action: string;
  missing_information: string[];
  disclaimer: string;
  ai_provider: string;
  created_at: string;
}

export interface LeadNote {
  id: string;
  author_id: string | null;
  body: string;
  created_at: string;
}

export interface LeadActivity {
  id: string;
  user_id: string | null;
  activity_type: ActivityType;
  description: string;
  event_metadata: Record<string, unknown>;
  created_at: string;
}

export interface ProductMatchSuggestion {
  product_id: string;
  product_name: string;
  projected_total_score: number;
  projected_fit_score: number;
  projected_need_score: number;
  reasons: string[];
}

export interface ExportLeadsRequest {
  format: "csv" | "csv_excel" | "json";
  status?: LeadStatus;
  priority?: LeadPriority;
  product_id?: string;
  company_id?: string;
  assigned_to?: string;
  min_score?: number;
}

export interface CreateLeadValues {
  company_id: string;
  product_id: string;
  contact_id: string | null;
  name: string;
  source: string;
  tags: string[];
}
