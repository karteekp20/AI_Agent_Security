// ============================================================================
// AUTH TYPES
// ============================================================================

export interface RegisterRequest {
  email: string;
  password: string;
  full_name: string;
  org_name: string;
}

export interface RegisterResponse {
  user_id: string;
  org_id: string;
  workspace_id: string;
  email: string;
  full_name: string;
  role: string;
  org_name: string;
  org_slug: string;
  workspace_name: string;
  access_token: string;
  refresh_token: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user_id: string;
  org_id: string;
  email: string;
  role: string;
  password_change_required?: boolean;
}

export interface RefreshTokenRequest {
  refresh_token: string;
}

export interface RefreshTokenResponse {
  access_token: string;
  token_type: string;
}

export interface CurrentUser {
  user_id: string;
  org_id: string;
  email: string;
  full_name: string;
  role: string;
  permissions: string[];
  is_active: boolean;
  mfa_enabled: boolean;
  created_at: string;
}

export interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
  confirm_password: string;
}

export interface ChangePasswordResponse {
  success: boolean;
  message: string;
}

// ============================================================================
// ORGANIZATION TYPES
// ============================================================================

export interface Organization {
  org_id: string;
  org_name: string;
  org_slug: string;
  subscription_tier: string;
  subscription_status: string;
  current_users: number;
  max_users: number;
  api_requests_this_month: number;
  max_api_requests_per_month: number;
  created_at: string;
}

export interface OrganizationStats {
  total_api_requests_this_month: number;
  total_users: number;
  total_workspaces: number;
  total_api_keys: number;
  total_policies: number;
  subscription_tier: string;
  usage_percentage: number;
}

export interface User {
  user_id: string;
  org_id: string;
  email: string;
  full_name: string;
  role: string;
  permissions: string[];
  is_active: boolean;
  mfa_enabled: boolean;
  last_login: string | null;
  created_at: string;
}

export interface InviteUserRequest {
  email: string;
  full_name: string;
  role: string;
  permissions?: string[];
}

export interface InviteUserResponse {
  user_id: string;
  email: string;
  full_name: string;
  role: string;
  temporary_password: string;
}

// ============================================================================
// WORKSPACE TYPES
// ============================================================================

export interface Workspace {
  workspace_id: string;
  org_id: string;
  workspace_name: string;
  workspace_slug: string;
  description: string | null;
  environment: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CreateWorkspaceRequest {
  workspace_name: string;
  description?: string;
  environment?: string;
}

// ============================================================================
// AUDIT LOG TYPES
// ============================================================================

export interface PIIEntityDetail {
  entity_type: string;
  masked_value?: string;  // Only for admin/owner users
  redaction_strategy: string;
  start_position: number;
  end_position: number;
  confidence: number;
  detection_method: string;
  token_id: string;
}

export interface InjectionDetail {
  injection_type: string;
  confidence: number;
  matched_patterns: string[];
  severity: string;
}

export interface ContentViolationDetail {
  violation_type: string;
  matched_terms: string[];
  severity: string;
}

export interface ThreatDetails {
  pii: PIIEntityDetail[];
  injections: InjectionDetail[];
  content_violations: ContentViolationDetail[];
  total_threat_count: number;
  blocking_reasons: string[];
}

export interface AuditLog {
  id: number;
  timestamp: string;
  session_id: string;
  request_id: string;
  org_id: string;
  workspace_id: string;
  user_id: string;
  user_input: string;
  blocked: boolean;
  risk_score: number;
  risk_level: string;
  pii_detected: boolean;
  injection_detected: boolean;
  threat_details?: ThreatDetails;  // NEW: Detailed threat information
}

// ============================================================================
// DASHBOARD TYPES
// ============================================================================

export interface DashboardMetrics {
  total_requests: number;
  threats_blocked: number;
  pii_detected: number;
  injection_attempts: number;
  avg_risk_score: number;
  risk_score_trend: Array<{ timestamp: string; risk_score: number }>;
  threat_distribution: Array<{ threat_type: string; count: number }>;
  threats_over_time?: Array<{ timestamp: string; count: number }>;
  pii_types?: Array<{ type: string; count: number }>;
  top_affected_users?: Array<{ user_id: string; threat_count: number }>;
  hourly_activity?: Array<{ hour: number; count: number }>;
}

export interface ThreatEvent {
  timestamp: string;
  threat_type: string;
  risk_score: number;
  blocked: boolean;
  user_input: string;
  user_id?: string;
  threat_count_by_type?: {
    pii?: number;
    injection?: number;
    content_violation?: number;
  };
}

export interface ThreatTypeCount {
  type: string;
  count: number;
  percentage: number;
}

export interface ThreatBreakdown {
  pii_types: ThreatTypeCount[];
  injection_types: ThreatTypeCount[];
  content_violations: ThreatTypeCount[];
  severity_distribution: {
    low: number;
    medium: number;
    high: number;
    critical: number;
  };
}

// ============================================================================
// POLICY TYPES
// ============================================================================

export interface Policy {
  policy_id: string;
  org_id: string;
  workspace_id: string | null;
  policy_name: string;
  policy_type: string;
  pattern_value: string;
  action: string;
  severity: string;
  description: string | null;
  is_active: boolean;
  test_percentage: number;
  triggered_count: number;
  false_positive_count: number;
  version: number;
  parent_policy_id: string | null;
  created_at: string;
  updated_at: string;
  deployed_at: string | null;
}

export interface CreatePolicyRequest {
  policy_name: string;
  policy_type: string;
  pattern_value: string;
  action?: string;
  severity?: string;
  description?: string;
  workspace_id?: string;
  is_active?: boolean;
  test_percentage?: number;
}

export interface UpdatePolicyRequest {
  policy_name?: string;
  pattern_value?: string;
  action?: string;
  severity?: string;
  description?: string;
  is_active?: boolean;
  test_percentage?: number;
}

export interface TestPolicyRequest {
  test_input: string;
}

export interface DeployPolicyRequest {
  test_percentage: number;
  description?: string;
}

// ============================================================================
// API RESPONSE TYPES
// ============================================================================

export interface ApiError {
  detail: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}
