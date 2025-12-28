import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts';

interface SeverityDistributionChartProps {
  totalRequests: number;
  avgRiskScore: number;
}

export function SeverityDistributionChart({ totalRequests, avgRiskScore }: SeverityDistributionChartProps) {
  // Calculate estimated distribution based on avg risk score
  // In a real implementation, this would come from the API
  // For now, we'll create a simple distribution
  const criticalPercent = Math.max(0, Math.min(25, (avgRiskScore - 0.8) * 100));
  const highPercent = Math.max(0, Math.min(35, (avgRiskScore - 0.5) * 80));
  const mediumPercent = Math.max(0, Math.min(30, avgRiskScore * 50));
  const lowPercent = Math.max(10, 100 - criticalPercent - highPercent - mediumPercent);

  const data = [
    {
      name: 'Low',
      value: Math.round((lowPercent / 100) * totalRequests),
      color: '#22c55e',  // green-500
      percentage: lowPercent.toFixed(1)
    },
    {
      name: 'Medium',
      value: Math.round((mediumPercent / 100) * totalRequests),
      color: '#eab308',  // yellow-500
      percentage: mediumPercent.toFixed(1)
    },
    {
      name: 'High',
      value: Math.round((highPercent / 100) * totalRequests),
      color: '#f97316',  // orange-500
      percentage: highPercent.toFixed(1)
    },
    {
      name: 'Critical',
      value: Math.round((criticalPercent / 100) * totalRequests),
      color: '#ef4444',  // red-500
      percentage: criticalPercent.toFixed(1)
    },
  ].filter(item => item.value > 0); // Only show non-zero values

  const RADIAN = Math.PI / 180;
  const renderCustomizedLabel = ({
    cx,
    cy,
    midAngle,
    innerRadius,
    outerRadius,
    percent,
  }: any) => {
    const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
    const x = cx + radius * Math.cos(-midAngle * RADIAN);
    const y = cy + radius * Math.sin(-midAngle * RADIAN);

    if (percent < 0.05) return null; // Don't show label if less than 5%

    return (
      <text
        x={x}
        y={y}
        fill="white"
        textAnchor={x > cx ? 'start' : 'end'}
        dominantBaseline="central"
        className="text-sm font-semibold"
      >
        {`${(percent * 100).toFixed(0)}%`}
      </text>
    );
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Severity Distribution</CardTitle>
        <CardDescription>
          Risk severity levels across all requests
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={220}>
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="45%"
              labelLine={false}
              label={renderCustomizedLabel}
              outerRadius={70}
              innerRadius={45}
              fill="#8884d8"
              dataKey="value"
              paddingAngle={2}
            >
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{
                backgroundColor: 'hsl(var(--background))',
                border: '1px solid hsl(var(--border))',
                borderRadius: '0.5rem',
              }}
              formatter={(value: number | undefined) => [value || 0, 'Requests']}
            />
            <Legend
              verticalAlign="bottom"
              height={36}
              iconType="circle"
              formatter={(value, entry: any) => {
                const item = data.find(d => d.name === value);
                return `${value} (${item?.percentage}%)`;
              }}
            />
          </PieChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
