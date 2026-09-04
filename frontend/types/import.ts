export type ImportEntityType = "company" | "contact" | "product" | "lead";
export type ImportJobStatus = "queued" | "running" | "completed" | "failed" | "cancelled";

export const IMPORT_ENTITY_TYPES: ImportEntityType[] = ["company", "contact", "product", "lead"];

export const IMPORT_ENTITY_LABELS: Record<ImportEntityType, string> = {
  company: "Companies",
  contact: "Contacts",
  product: "Products",
  lead: "Leads",
};

export const IMPORT_TEMPLATE_COLUMNS: Record<ImportEntityType, string[]> = {
  company: [
    "name",
    "website",
    "industry",
    "locations",
    "company_size",
    "revenue_range",
    "business_description",
    "technology_stack",
    "business_challenges",
    "public_signals",
    "confidence_score",
  ],
  contact: [
    "company_website",
    "full_name",
    "job_title",
    "department",
    "seniority",
    "role_relevance",
    "profile_url",
    "business_email",
    "business_phone",
    "confidence_score",
  ],
  product: [
    "name",
    "code",
    "short_description",
    "detailed_description",
    "target_industries",
    "target_company_size",
    "target_geographic_regions",
    "business_problems",
    "key_features",
    "benefits",
    "pricing_model",
    "minimum_contract_value",
    "required_technical_capabilities",
    "supported_integrations",
    "ideal_customer_profile",
    "common_use_cases",
    "competitor_alternatives",
  ],
  lead: ["company_website", "product_code", "contact_email", "name", "source", "tags"],
};

export interface RowError {
  row: number;
  errors: string[];
}

export interface ImportPreview {
  entity_type: ImportEntityType;
  total_rows: number;
  missing_required_columns: string[];
  unknown_columns: string[];
  valid_row_count: number;
  invalid_row_count: number;
  sample_errors: RowError[];
  can_proceed: boolean;
}

export interface ImportJob {
  id: string;
  entity_type: ImportEntityType;
  status: ImportJobStatus;
  file_name: string;
  progress_percentage: number;
  current_step: string;
  logs: string[];
  total_rows: number;
  processed_rows: number;
  created_count: number;
  skipped_count: number;
  error_count: number;
  row_errors: RowError[];
  error_message: string;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}
