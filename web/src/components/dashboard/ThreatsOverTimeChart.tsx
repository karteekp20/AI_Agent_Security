import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface ThreatTimeDataPoint {
  timestamp: string;
  count: number;
}

interface ThreatsOverTimeChartProps {
  data: ThreatTimeDataPoint[];
  timeframe: string;
}

export function ThreatsOverTimeChart({ data, timeframe }: ThreatsOverTimeChartProps) {
  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);

    if (timeframe === '1h') {
      return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
    } else if (timeframe === '24h') {
      return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
    } else if (timeframe === '7d') {
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    } else {
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    }
  };

  const chartData = data.map((point) => ({
    time: formatTimestamp(point.timestamp),
    count: point.count,
  }));

  return (
    <Card>
      <CardHeader>
        <CardTitle>Threats Over Time</CardTitle>
        <CardDescription>
          Threat detection trend
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={220}>
          <AreaChart data={chartData}>
            <defs>
              <linearGradient id="colorThreats" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3}/>
                <stop offset="95%" stopColor="#ef4444" stopOpacity={0}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis
              dataKey="time"
              className="text-xs"
              tick={{ fill: 'hsl(var(--muted-foreground))' }}
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
              formatter={(value: number) => [value, 'Threats']}
            />
            <Area
              type="monotone"
              dataKey="count"
              stroke="#ef4444"
              strokeWidth={2}
              fill="url(#colorThreats)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
