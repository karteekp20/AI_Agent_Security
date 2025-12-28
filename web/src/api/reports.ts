/**
 * Reports API Client
 */

import { apiClient } from './client';

export interface Report {
  report_id: string;
  org_id: string;
  workspace_id?: string;
  report_name: string;
  report_type: string;
  description?: string;
  date_range_start: string;
  date_range_end: string;
  file_format: string;
  file_url?: string;
  file_size_bytes: number;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress_percentage: number;
  error_message?: string;
  total_requests_analyzed: number;
  threats_detected: number;
  pii_instances: number;
  injections_blocked: number;
  generated_by?: string;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  expires_at?: string;
}

export interface GenerateReportRequest {
  report_name: string;
  report_type: 'pci_dss' | 'gdpr' | 'hipaa' | 'soc2';
  file_format: 'pdf' | 'excel' | 'json';
  date_range_start: string;
  date_range_end: string;
  workspace_id?: string;
  description?: string;
}

export interface ReportListResponse {
  reports: Report[];
  total: number;
  page: number;
  page_size: number;
}

export const reportsApi = {
  /**
   * Generate new report (async)
   */
  generateReport: async (request: GenerateReportRequest): Promise<Report> => {
    const response = await apiClient.post<Report>('/reports', request);
    return response.data;
  },

  /**
   * List all reports
   */
  listReports: async (params: {
    report_type?: string;
    status?: string;
    page?: number;
    page_size?: number;
  } = {}): Promise<ReportListResponse> => {
    const queryParams = new URLSearchParams();
    if (params.report_type) queryParams.append('report_type', params.report_type);
    if (params.status) queryParams.append('status', params.status);
    if (params.page) queryParams.append('page', params.page.toString());
    if (params.page_size) queryParams.append('page_size', params.page_size.toString());

    const response = await apiClient.get<ReportListResponse>(`/reports?${queryParams.toString()}`);
    return response.data;
  },

  /**
   * Get report details
   */
  getReport: async (reportId: string): Promise<Report> => {
    const response = await apiClient.get<Report>(`/reports/${reportId}`);
    return response.data;
  },

  /**
   * Download report file
   */
  downloadReport: async (reportId: string): Promise<Blob> => {
    const response = await apiClient.get(`/reports/${reportId}/download`, {
      responseType: 'blob',
    });
    return response.data;
  },

  /**
   * Delete report
   */
  deleteReport: async (reportId: string): Promise<void> => {
    await apiClient.delete(`/reports/${reportId}`);
  },
};
