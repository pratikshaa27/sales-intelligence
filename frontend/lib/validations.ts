import { z } from "zod";

const passwordSchema = z
  .string()
  .min(12, "Password must be at least 12 characters")
  .refine((v) => /[A-Z]/.test(v), "Password must contain an uppercase letter")
  .refine((v) => /[0-9]/.test(v), "Password must contain a digit");

export const loginSchema = z.object({
  email: z.string().email("Enter a valid email address"),
  password: z.string().min(1, "Password is required"),
});
export type LoginFormValues = z.infer<typeof loginSchema>;

export const registerSchema = z.object({
  organization_name: z.string().min(2, "Organization name is required"),
  admin_full_name: z.string().min(2, "Your name is required"),
  admin_email: z.string().email("Enter a valid email address"),
  admin_password: passwordSchema,
});
export type RegisterFormValues = z.infer<typeof registerSchema>;

export const forgotPasswordSchema = z.object({
  email: z.string().email("Enter a valid email address"),
});
export type ForgotPasswordFormValues = z.infer<typeof forgotPasswordSchema>;

export const resetPasswordSchema = z.object({
  token: z.string().min(1, "Reset token is required"),
  new_password: passwordSchema,
});
export type ResetPasswordFormValues = z.infer<typeof resetPasswordSchema>;

export const productFormSchema = z.object({
  name: z.string().min(2, "Product name is required").max(255),
  code: z.string().min(1, "Product code is required").max(64),
  category_id: z.string().uuid().nullable(),
  short_description: z.string().max(500).default(""),
  detailed_description: z.string().default(""),
  target_industries: z.array(z.string()).default([]),
  target_company_size: z.array(z.string()).default([]),
  target_geographic_regions: z.array(z.string()).default([]),
  business_problems: z.array(z.string()).default([]),
  key_features: z.array(z.string()).default([]),
  benefits: z.array(z.string()).default([]),
  pricing_model: z.string().default(""),
  minimum_contract_value: z.number().nullable().default(null),
  required_technical_capabilities: z.array(z.string()).default([]),
  supported_integrations: z.array(z.string()).default([]),
  ideal_customer_profile: z.string().default(""),
  common_use_cases: z.array(z.string()).default([]),
  competitor_alternatives: z.array(z.string()).default([]),
});
export type ProductFormSchemaValues = z.infer<typeof productFormSchema>;

export const companyFormSchema = z.object({
  name: z.string().min(1, "Company name is required").max(255),
  website: z.string().min(1, "Website is required so the company can be de-duplicated"),
  industry: z.string().default(""),
  locations: z.array(z.string()).default([]),
  company_size: z.string().default(""),
  revenue_range: z.string().default(""),
  business_description: z.string().default(""),
  technology_stack: z.array(z.string()).default([]),
  business_challenges: z.array(z.string()).default([]),
  public_signals: z.array(z.string()).default([]),
  confidence_score: z.number().min(0).max(100).default(0),
});
export type CompanyFormSchemaValues = z.infer<typeof companyFormSchema>;

export const contactFormSchema = z.object({
  company_id: z.string().uuid("Select a company"),
  full_name: z.string().min(1, "Full name is required").max(255),
  job_title: z.string().default(""),
  department: z.string().default(""),
  seniority: z.string().default(""),
  role_relevance: z.string().default(""),
  profile_url: z.string().default(""),
  business_email: z.string().default(""),
  business_phone: z.string().default(""),
  confidence_score: z.number().min(0).max(100).default(0),
});
export type ContactFormSchemaValues = z.infer<typeof contactFormSchema>;

export const createLeadFormSchema = z.object({
  company_id: z.string().uuid("Select a company"),
  product_id: z.string().uuid("Select a product"),
  contact_id: z.string().default(""),
  name: z.string().min(1, "Lead name is required").max(255),
  source: z.string().default("manual"),
  tags: z.array(z.string()).default([]),
});
export type CreateLeadFormValues = z.infer<typeof createLeadFormSchema>;

export const discoverCompaniesFormSchema = z.object({
  industry: z.string().default(""),
  location: z.string().default(""),
  company_size: z.string().default(""),
  keywords: z.array(z.string()).default([]),
  number_of_companies: z.number().min(1).max(20).default(5),
});
export type DiscoverCompaniesFormValues = z.infer<typeof discoverCompaniesFormSchema>;
