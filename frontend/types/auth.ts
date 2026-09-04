export interface User {
  id: string;
  email: string;
  full_name: string;
  is_email_verified: boolean;
  is_superadmin: boolean;
}

export interface AccessTokenResponse {
  access_token: string;
  token_type: string;
  expires_in_minutes: number;
  user: User;
  organization_id: string;
  role: string;
  csrf_token: string;
}

export interface MeResponse {
  user: User;
  organization_id: string;
  organization_name: string;
  role: string;
  permissions: string[];
}

export interface ApiSuccess<T> {
  success: true;
  data: T;
  message: string;
}

export interface ApiError {
  success: false;
  error: {
    code: string;
    message: string;
    details: Record<string, unknown>;
  };
  request_id?: string;
}
