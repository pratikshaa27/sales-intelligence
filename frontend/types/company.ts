export type ResearchStatus = "not_researched" | "researching" | "researched" | "failed";
export type SourceType = "website" | "directory" | "news" | "job_posting" | "social_profile" | "other";

export interface CompanySource {
  id: string;
  url: string;
  title: string;
  source_type: SourceType;
  published_at: string | null;
  created_at: string;
}

export interface CompanyFormValues {
  name: string;
  website: string;
  industry: string;
  locations: string[];
  company_size: string;
  revenue_range: string;
  business_description: string;
  technology_stack: string[];
  business_challenges: string[];
  public_signals: string[];
  confidence_score: number;
}

export interface Company extends CompanyFormValues {
  id: string;
  organization_id: string;
  domain: string;
  research_status: ResearchStatus;
  created_at: string;
  updated_at: string;
}

export interface CompanyListItem {
  id: string;
  name: string;
  domain: string;
  website: string;
  industry: string;
  company_size: string;
  confidence_score: number;
  research_status: ResearchStatus;
  created_at: string;
}
