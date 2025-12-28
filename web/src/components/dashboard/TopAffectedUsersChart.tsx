import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface UserThreatData {
  user_id: string;
  threat_count: number;
}

interface TopAffectedUsersChartProps {
  data: UserThreatData[];
}

export function TopAffectedUsersChart({ data }: TopAffectedUsersChartProps) {
  const chartData = data
    .sort((a, b) => b.threat_count - a.threat_count)
    .slice(0, 10)
    .map((item) => ({
      user: item.user_id.length > 15 ? `${item.user_id.substring(0, 15)}...` : item.user_id,
      count: item.threat_count,
    }));

  return (
    <Card>
      <CardHeader>
        <CardTitle>Top Affected Users</CardTitle>
        <CardDescription>
          Users with most threats detected
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={chartData} layout="vertical">
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis
              type="number"
              className="text-xs"
              tick={{ fill: 'hsl(var(--muted-foreground))' }}
            />
            <YAxis
              type="category"
              dataKey="user"
              className="text-xs"
              tick={{ fill: 'hsl(var(--muted-foreground))' }}
              width={100}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: 'hsl(var(--background))',
                border: '1px solid hsl(var(--border))',
                borderRadius: '0.5rem',
              }}
              formatter={(value: number) => [value, 'Threats']}
            />
            <Bar
              dataKey="count"
              fill="#f97316"
              radius={[0, 4, 4, 0]}
            />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
