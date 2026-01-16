import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts';
import type { ThreatBreakdown } from '@/api/types';

interface ThreatBreakdownCardProps {
  data: ThreatBreakdown | null;
  timeframe: string;
  isLoading?: boolean;
}

const THREAT_COLORS = ['#ef4444', '#f97316', '#eab308', '#3b82f6', '#8b5cf6', '#ec4899', '#14b8a6'];

export function ThreatBreakdownCard({ data, timeframe, isLoading }: ThreatBreakdownCardProps) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Threat Breakdown</CardTitle>
          <CardDescription>Last {timeframe}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="animate-pulse space-y-4">
            <div className="h-48 bg-gray-200 dark:bg-gray-700 rounded" />
            <div className="space-y-2">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-8 bg-gray-200 dark:bg-gray-700 rounded" />
              ))}
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!data) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Threat Breakdown</CardTitle>
          <CardDescription>Last {timeframe}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8 text-gray-500 dark:text-gray-400">
            No threat data available
          </div>
        </CardContent>
      </Card>
    );
  }

  // Combine all threat types for pie chart
  const allThreats = [
    ...data.pii_types.map(t => ({ name: `PII: ${t.type}`, value: t.count, category: 'PII' })),
    ...data.injection_types.map(t => ({ name: `Injection: ${t.type}`, value: t.count, category: 'Injection' })),
    ...data.content_violations.map(t => ({ name: `Violation: ${t.type}`, value: t.count, category: 'Violation' })),
  ].slice(0, 7); // Top 7 threats

  const topThreats = [
    ...data.pii_types,
    ...data.injection_types,
    ...data.content_violations,
  ]
    .sort((a, b) => b.count - a.count)
    .slice(0, 5);

  const totalThreats = allThreats.reduce((sum, t) => sum + t.value, 0);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Threat Breakdown</CardTitle>
        <CardDescription>Last {timeframe}</CardDescription>
      </CardHeader>
      <CardContent>
        {totalThreats > 0 ? (
          <>
            {/* Pie Chart */}
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie
                  data={allThreats}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ percent }) => (percent > 0.05 ? `${(percent * 100).toFixed(0)}%` : '')}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {allThreats.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={THREAT_COLORS[index % THREAT_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>

            {/* Top Threat Types List */}
            <div className="mt-6 space-y-3">
              <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300">
                Top Threat Types
              </h4>
              {topThreats.map((threat, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between p-2 rounded hover:bg-gray-50 dark:hover:bg-gray-900/50"
                >
                  <div className="flex items-center gap-2">
                    <div
                      className="w-3 h-3 rounded-full"
                      style={{ backgroundColor: THREAT_COLORS[idx % THREAT_COLORS.length] }}
                    />
                    <span className="text-sm text-gray-700 dark:text-gray-300">
                      {threat.type}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline">{threat.count}</Badge>
                    <span className="text-xs text-gray-500 dark:text-gray-400">
                      {threat.percentage.toFixed(1)}%
                    </span>
                  </div>
                </div>
              ))}
            </div>

            {/* Severity Distribution */}
            <div className="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700">
              <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
                Severity Distribution
              </h4>
              <div className="grid grid-cols-2 gap-2">
                {Object.entries(data.severity_distribution).map(([severity, count]) => (
                  <div
                    key={severity}
                    className="flex items-center justify-between p-2 rounded bg-gray-50 dark:bg-gray-900/50"
                  >
                    <span className="text-xs capitalize text-gray-600 dark:text-gray-400">
                      {severity}
                    </span>
                    <Badge
                      className={
                        severity === 'critical'
                          ? 'bg-red-600'
                          : severity === 'high'
                          ? 'bg-orange-600'
                          : severity === 'medium'
                          ? 'bg-yellow-600'
                          : 'bg-blue-600'
                      }
                    >
                      {count}
                    </Badge>
                  </div>
                ))}
              </div>
            </div>
          </>
        ) : (
          <div className="text-center py-8 text-gray-500 dark:text-gray-400">
            No threats detected in this period
          </div>
        )}
      </CardContent>
    </Card>
  );
}
