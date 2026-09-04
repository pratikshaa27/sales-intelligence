export type JobType = "company_discovery" | "company_research";
export type JobStatus = "queued" | "running" | "completed" | "failed" | "cancelled";

export interface ResearchJob {
  id: string;
  job_type: JobType;
  status: JobStatus;
  input_parameters: Record<string, unknown>;
  progress_percentage: number;
  current_step: string;
  logs: string[];
  result_summary: Record<string, unknown>;
  error_message: string;
  retry_count: number;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface DiscoveredCompanyCandidate {
  name: string;
  website: string;
  domain: string;
  industry: string;
  company_size: string;
  rationale: string;
  already_exists: boolean;
}

export interface DiscoveryResultSummary {
  candidates: DiscoveredCompanyCandidate[];
  is_mock_data: boolean;
  provider: string;
}

export type EvidenceCategory =
  | "overview"
  | "technology_stack"
  | "hiring_signal"
  | "expansion_signal"
  | "digital_transformation_signal"
  | "security_signal"
  | "business_challenge"
  | "other";

export interface ResearchEvidence {
  id: string;
  category: EvidenceCategory;
  fact_text: string;
  source_url: string;
  source_title: string;
  source_type: string;
  source_published_at: string | null;
  retrieved_at: string;
  confidence: number;
  is_ai_generated: boolean;
}
