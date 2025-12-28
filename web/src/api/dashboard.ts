import { apiClient } from './client';
import type { DashboardMetrics, ThreatEvent } from './types';

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
