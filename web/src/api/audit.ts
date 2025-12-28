/**
 * Audit Logs API Client
 */

import { apiClient } from './client';

export interface AuditLog {
  id: number;
  timestamp: string;
  session_id: string;
  request_id?: string;
  org_id?: string;
  workspace_id?: string;
  user_id?: string;
  user_role?: string;
  ip_address?: string;
  user_input: string;
  input_length: number;
  blocked: boolean;
  risk_score?: number;
  risk_level?: string;
  pii_detected: boolean;
  pii_entities?: Record<string, any>;
  redacted_count: number;
  injection_detected: boolean;
  injection_type?: string;
  injection_confidence?: number;
  escalated: boolean;
  escalated_to?: string;
  metadata?: Record<string, any>;
}

export interface AuditLogListResponse {
  logs: AuditLog[];
  total: number;
  page: number;
  page_size: number;
}

export interface AuditLogFilters {
  start_date?: string;
  end_date?: string;
  workspace_id?: string;
  user_id?: string;
  blocked_only?: boolean;
  pii_only?: boolean;
  injection_only?: boolean;
  min_risk_score?: number;
  search?: string;
  page?: number;
  page_size?: number;
}

export const auditApi = {
  /**
   * List audit logs with filtering
   */
  listAuditLogs: async (filters: AuditLogFilters = {}): Promise<AuditLogListResponse> => {
    const params = new URLSearchParams();

    if (filters.start_date) params.append('start_date', filters.start_date);
    if (filters.end_date) params.append('end_date', filters.end_date);
    if (filters.workspace_id) params.append('workspace_id', filters.workspace_id);
    if (filters.user_id) params.append('user_id', filters.user_id);
    if (filters.blocked_only) params.append('blocked_only', 'true');
    if (filters.pii_only) params.append('pii_only', 'true');
    if (filters.injection_only) params.append('injection_only', 'true');
    if (filters.min_risk_score !== undefined) params.append('min_risk_score', filters.min_risk_score.toString());
    if (filters.search) params.append('search', filters.search);
    if (filters.page) params.append('page', filters.page.toString());
    if (filters.page_size) params.append('page_size', filters.page_size.toString());

    const response = await apiClient.get<AuditLogListResponse>(`/audit-logs?${params.toString()}`);
    return response.data;
  },

  /**
   * Get single audit log by ID
   */
  getAuditLog: async (logId: number): Promise<AuditLog> => {
    const response = await apiClient.get<AuditLog>(`/audit-logs/${logId}`);
    return response.data;
  },
};
