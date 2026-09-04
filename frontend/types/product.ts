export type ProductStatus = "draft" | "active" | "archived";
export type EmbeddingStatus = "none" | "queued" | "processing" | "completed" | "failed";

export interface ProductCategory {
  id: string;
  name: string;
  description: string;
}

export interface ProductDocument {
  id: string;
  file_name: string;
  content_type: string;
  size_bytes: number;
  created_at: string;
}

export interface ProductFormValues {
  name: string;
  code: string;
  category_id: string | null;
  short_description: string;
  detailed_description: string;
  target_industries: string[];
  target_company_size: string[];
  target_geographic_regions: string[];
  business_problems: string[];
  key_features: string[];
  benefits: string[];
  pricing_model: string;
  minimum_contract_value: number | null;
  required_technical_capabilities: string[];
  supported_integrations: string[];
  ideal_customer_profile: string;
  common_use_cases: string[];
  competitor_alternatives: string[];
}

export interface Product extends ProductFormValues {
  id: string;
  organization_id: string;
  status: ProductStatus;
  embedding_status: EmbeddingStatus;
  category: ProductCategory | null;
  created_at: string;
  updated_at: string;
}

export interface ProductListItem {
  id: string;
  name: string;
  code: string;
  short_description: string;
  status: ProductStatus;
  embedding_status: EmbeddingStatus;
  category: ProductCategory | null;
  target_industries: string[];
  created_at: string;
  updated_at: string;
}

export interface PaginationMeta {
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

export interface PaginatedData<T> {
  items: T[];
  pagination: PaginationMeta;
}
