import { apiClient } from './client';
import type { DashboardMetrics, ThreatEvent, ThreatBreakdown } from './types';

/**
 * Get dashboard metrics for specified timeframe
 */
export const getDashboardMetrics = async (timeframe: string = '24h'): Promise<DashboardMetrics> => {
  const response = await apiClient.get<DashboardMetrics>(`/dashboard/metrics`, {
    params: { timeframe },
  });
  return response.data;
};

/**
 * Get recent threat events
 */
export const getRecentThreats = async (limit: number = 50): Promise<ThreatEvent[]> => {
  const response = await apiClient.get<ThreatEvent[]>(`/dashboard/recent-threats`, {
    params: { limit },
  });
  return response.data;
};

/**
 * Get threat breakdown statistics
 */
export const getThreatBreakdown = async (timeframe: string = '24h'): Promise<ThreatBreakdown> => {
  const response = await apiClient.get<ThreatBreakdown>(`/dashboard/threat-breakdown`, {
    params: { timeframe },
  });
  return response.data;
};
