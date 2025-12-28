import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';

interface ThreatDistribution {
  threat_type: string;
  count: number;
}

interface ThreatDistributionChartProps {
  data: ThreatDistribution[];
}

// Color mapping for different threat types
const THREAT_COLORS: Record<string, string> = {
  'SQL Injection': '#ef4444',              // red-500
  'XSS (Cross-Site Scripting)': '#f97316', // orange-500
  'Prompt Injection': '#eab308',            // yellow-500
  'PII Leak': '#3b82f6',                    // blue-500
  'Path Traversal': '#8b5cf6',              // violet-500
  'Template Injection': '#ec4899',          // pink-500
  'Code Injection': '#f43f5e',              // rose-500
};

const DEFAULT_COLOR = '#6b7280'; // gray-500

export function ThreatDistributionChart({ data }: ThreatDistributionChartProps) {
  const chartData = data.map((item) => ({
    name: item.threat_type,
    count: item.count,
    color: THREAT_COLORS[item.threat_type] || DEFAULT_COLOR,
  }));

  return (
    <Card>
      <CardHeader>
        <CardTitle>Threat Distribution</CardTitle>
        <CardDescription>
          Breakdown of detected threats by type
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis
              dataKey="name"
              className="text-xs"
              tick={{ fill: 'hsl(var(--muted-foreground))' }}
              angle={-45}
              textAnchor="end"
              height={80}
            />
            <YAxis
              className="text-xs"
              tick={{ fill: 'hsl(var(--muted-foreground))' }}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: 'hsl(var(--background))',
                border: '1px solid hsl(var(--border))',
                borderRadius: '0.5rem',
              }}
              formatter={(value: number) => [value, 'Count']}
            />
            <Bar
              dataKey="count"
              radius={[4, 4, 0, 0]}
            >
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
