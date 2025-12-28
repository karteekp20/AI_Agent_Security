/**
 * React Query Hooks for Reports
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { reportsApi } from '@/api/reports';
import type { GenerateReportRequest } from '@/api/reports';

export function useReports(filters: {
  report_type?: string;
  status?: string;
  page?: number;
  page_size?: number;
} = {}) {
  return useQuery({
    queryKey: ['reports', filters],
    queryFn: () => reportsApi.listReports(filters),
    refetchInterval: (data) => {
      // Only poll if there are pending or processing reports
      const hasActiveReports = data?.reports?.some(
        (report: any) => report.status === 'pending' || report.status === 'processing'
      );
      return hasActiveReports ? 5000 : false; // Poll every 5s only if needed
    },
  });
}

export function useReport(reportId: string | null) {
  return useQuery({
    queryKey: ['report', reportId],
    queryFn: () => reportsApi.getReport(reportId!),
    enabled: reportId !== null,
    refetchInterval: (data) => {
      // Poll every 2 seconds if report is pending or processing
      if (data?.status === 'pending' || data?.status === 'processing') {
        return 2000;
      }
      return false;
    },
  });
}

export function useGenerateReport() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: GenerateReportRequest) => reportsApi.generateReport(request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reports'] });
    },
  });
}

export function useDeleteReport() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (reportId: string) => reportsApi.deleteReport(reportId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reports'] });
    },
  });
}

export function useDownloadReport() {
  return useMutation({
    mutationFn: async ({ reportId, filename }: { reportId: string; filename: string }) => {
      const blob = await reportsApi.downloadReport(reportId);
      // Create download link
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    },
  });
}
