import type { SourceType } from "@/types/company";

export type VerificationStatus = "unverified" | "verified" | "disputed";

export interface ContactSource {
  id: string;
  url: string;
  title: string;
  source_type: SourceType;
  published_at: string | null;
  created_at: string;
}

export interface ContactFormValues {
  company_id: string;
  full_name: string;
  job_title: string;
  department: string;
  seniority: string;
  role_relevance: string;
  profile_url: string;
  business_email: string;
  business_phone: string;
  confidence_score: number;
}

export interface Contact extends ContactFormValues {
  id: string;
  organization_id: string;
  verification_status: VerificationStatus;
  created_at: string;
  updated_at: string;
}

export interface ContactListItem {
  id: string;
  company_id: string;
  company_name: string;
  products: string[];
  full_name: string;
  job_title: string;
  seniority: string;
  verification_status: VerificationStatus;
  confidence_score: number;
  created_at: string;
}
