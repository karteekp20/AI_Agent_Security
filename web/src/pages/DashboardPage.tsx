import { useState } from 'react';
import { useCurrentUser, useLogout } from '@/hooks/useAuth';
import { useDashboardMetrics, useRecentThreats, useThreatBreakdown } from '@/hooks/useDashboard';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Shield, LogOut, Loader2, Activity, AlertTriangle, Eye, TrendingUp } from 'lucide-react';
import { MetricCard } from '@/components/dashboard/MetricCard';
import { RiskScoreChart } from '@/components/dashboard/RiskScoreChart';
import { ThreatDistributionChart } from '@/components/dashboard/ThreatDistributionChart';
import { RequestStatusChart } from '@/components/dashboard/RequestStatusChart';
import { SeverityDistributionChart } from '@/components/dashboard/SeverityDistributionChart';
import { ThreatsOverTimeChart } from '@/components/dashboard/ThreatsOverTimeChart';
import { PIITypesChart } from '@/components/dashboard/PIITypesChart';
import { TopAffectedUsersChart } from '@/components/dashboard/TopAffectedUsersChart';
import { AttackTimingChart } from '@/components/dashboard/AttackTimingChart';
import { DetectionRateGauge } from '@/components/dashboard/DetectionRateGauge';
import { TimeframeSelector } from '@/components/dashboard/TimeframeSelector';
import { RecentThreats } from '@/components/dashboard/RecentThreats';
import { ThreatBreakdownCard } from '@/components/dashboard/ThreatBreakdownCard';

export function DashboardPage() {
  const [timeframe, setTimeframe] = useState('24h');

  const { data: user, isLoading: userLoading } = useCurrentUser();
  const { data: metrics, isLoading: metricsLoading, error: metricsError } = useDashboardMetrics(timeframe);
  const { data: threats, isLoading: threatsLoading } = useRecentThreats(50);
  const { data: threatBreakdown, isLoading: breakdownLoading } = useThreatBreakdown(timeframe);
  const { mutate: logout } = useLogout();

  if (userLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950">
      {/* Header */}
      <header className="border-b bg-white dark:bg-slate-900 sticky top-0 z-10">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <Shield className="h-6 w-6 text-primary" />
            <div>
              <h1 className="text-xl font-bold">Sentinel</h1>
              <p className="text-xs text-muted-foreground">AI Security Platform</p>
            </div>
          </div>
          <div className="flex items-center space-x-4">
            <div className="text-sm text-right hidden md:block">
              <div className="font-medium">{user?.full_name}</div>
              <div className="text-muted-foreground">{user?.email}</div>
              <Badge variant="outline" className="mt-1">
                {user?.role?.toUpperCase()}
              </Badge>
            </div>
            <Button variant="outline" size="sm" onClick={() => logout()}>
              <LogOut className="h-4 w-4 mr-2" />
              Logout
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8">
        <div className="space-y-6">
          {/* Title and Timeframe Selector */}
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div>
              <h2 className="text-3xl font-bold">Dashboard</h2>
              <p className="text-muted-foreground mt-1">
                Real-time security monitoring and analytics
              </p>
            </div>
            <TimeframeSelector value={timeframe} onChange={setTimeframe} />
          </div>

          {/* Error State */}
          {metricsError && (
            <div className="p-4 rounded-lg bg-destructive/10 border border-destructive/20 text-destructive">
              Failed to load dashboard metrics. Please ensure the backend server is running.
            </div>
          )}

          {/* Loading State */}
          {metricsLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
          ) : (
            <>
              {/* Metrics Cards */}
              <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
                <MetricCard
                  title="Total Requests"
                  value={metrics?.total_requests.toLocaleString() || '0'}
                  subtitle={`Last ${timeframe === '1h' ? 'hour' : timeframe === '24h' ? '24 hours' : timeframe === '7d' ? '7 days' : '30 days'}`}
                  icon={Activity}
                />

                <MetricCard
                  title="Threats Blocked"
                  value={metrics?.threats_blocked.toLocaleString() || '0'}
                  subtitle={`Last ${timeframe === '1h' ? 'hour' : timeframe === '24h' ? '24 hours' : timeframe === '7d' ? '7 days' : '30 days'}`}
                  icon={AlertTriangle}
                  valueClassName="text-destructive"
                />

                <MetricCard
                  title="PII Detected"
                  value={metrics?.pii_detected.toLocaleString() || '0'}
                  subtitle={`Last ${timeframe === '1h' ? 'hour' : timeframe === '24h' ? '24 hours' : timeframe === '7d' ? '7 days' : '30 days'}`}
                  icon={Eye}
                  valueClassName="text-orange-500"
                />

                <MetricCard
                  title="Avg Risk Score"
                  value={metrics?.avg_risk_score.toFixed(3) || '0.000'}
                  subtitle={`Last ${timeframe === '1h' ? 'hour' : timeframe === '24h' ? '24 hours' : timeframe === '7d' ? '7 days' : '30 days'}`}
                  icon={TrendingUp}
                />
              </div>

              {/* Charts */}
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {/* Row 1: Core Metrics */}
                {metrics?.risk_score_trend && metrics.risk_score_trend.length > 0 && (
                  <RiskScoreChart
                    data={metrics.risk_score_trend}
                    timeframe={timeframe}
                  />
                )}

                {metrics?.threats_over_time && metrics.threats_over_time.length > 0 && (
                  <ThreatsOverTimeChart
                    data={metrics.threats_over_time}
                    timeframe={timeframe}
                  />
                )}

                {metrics && (
                  <DetectionRateGauge
                    totalRequests={metrics.total_requests}
                    threatsBlocked={metrics.threats_blocked}
                  />
                )}

                {/* Row 2: Distribution Analysis */}
                {metrics?.threat_distribution && metrics.threat_distribution.length > 0 && (
                  <ThreatDistributionChart data={metrics.threat_distribution} />
                )}

                {metrics?.pii_types && metrics.pii_types.length > 0 && (
                  <PIITypesChart data={metrics.pii_types} />
                )}

                {metrics && (
                  <SeverityDistributionChart
                    totalRequests={metrics.total_requests}
                    avgRiskScore={metrics.avg_risk_score}
                  />
                )}

                {/* NEW: Threat Breakdown Card */}
                <ThreatBreakdownCard
                  data={threatBreakdown || null}
                  timeframe={timeframe}
                  isLoading={breakdownLoading}
                />

                {/* Row 3: User & Timing Analysis */}
                {metrics?.top_affected_users && metrics.top_affected_users.length > 0 && (
                  <TopAffectedUsersChart data={metrics.top_affected_users} />
                )}

                {metrics?.hourly_activity && metrics.hourly_activity.length > 0 && (
                  <AttackTimingChart data={metrics.hourly_activity} />
                )}

                {metrics && (
                  <RequestStatusChart
                    totalRequests={metrics.total_requests}
                    threatsBlocked={metrics.threats_blocked}
                  />
                )}
              </div>

              {/* Recent Threats */}
              {threatsLoading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin text-primary" />
                </div>
              ) : (
                threats && <RecentThreats threats={threats} />
              )}
            </>
          )}
        </div>
      </main>
    </div>
  );
}
