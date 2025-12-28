/**
 * React Query Hooks for Audit Logs
 */

import { useQuery } from '@tanstack/react-query';
import { auditApi } from '@/api/audit';
import type { AuditLogFilters } from '@/api/audit';

export function useAuditLogs(filters: AuditLogFilters = {}) {
  return useQuery({
    queryKey: ['auditLogs', filters],
    queryFn: () => auditApi.listAuditLogs(filters),
    staleTime: 30000, // 30 seconds
  });
}

export function useAuditLog(logId: number | null) {
  return useQuery({
    queryKey: ['auditLog', logId],
    queryFn: () => auditApi.getAuditLog(logId!),
    enabled: logId !== null,
  });
}
