import { useQuery } from '@tanstack/react-query';
import * as dashboardApi from '@/api/dashboard';

/**
 * Hook to fetch dashboard metrics
 */
export function useDashboardMetrics(timeframe: string = '24h') {
  return useQuery({
    queryKey: ['dashboardMetrics', timeframe],
    queryFn: () => dashboardApi.getDashboardMetrics(timeframe),
    refetchInterval: 30000, // Refetch every 30 seconds
    staleTime: 20000, // Consider data stale after 20 seconds
  });
}

/**
 * Hook to fetch recent threats
 */
export function useRecentThreats(limit: number = 50) {
  return useQuery({
    queryKey: ['recentThreats', limit],
    queryFn: () => dashboardApi.getRecentThreats(limit),
    refetchInterval: 10000, // Refetch every 10 seconds for real-time feel
    staleTime: 5000, // Consider data stale after 5 seconds
  });
}
