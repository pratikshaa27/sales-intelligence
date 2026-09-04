export interface AuditLogEntry {
  id: string;
  organization_id: string | null;
  user_id: string | null;
  action: string;
  resource_type: string;
  resource_id: string;
  ip_address: string;
  user_agent: string;
  event_metadata: Record<string, unknown>;
  created_at: string;
}
