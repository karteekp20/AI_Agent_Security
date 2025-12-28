import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface RiskScoreDataPoint {
  timestamp: string;
  risk_score: number;
}

interface RiskScoreChartProps {
  data: RiskScoreDataPoint[];
  timeframe: string;
}

export function RiskScoreChart({ data, timeframe }: RiskScoreChartProps) {
  // Format timestamp based on timeframe
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
    riskScore: point.risk_score,
  }));

  return (
    <Card>
      <CardHeader>
        <CardTitle>Risk Score Trend</CardTitle>
        <CardDescription>
          Average risk score over time
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis
              dataKey="time"
              className="text-xs"
              tick={{ fill: 'hsl(var(--muted-foreground))' }}
            />
            <YAxis
              domain={[0, 1]}
              className="text-xs"
              tick={{ fill: 'hsl(var(--muted-foreground))' }}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: 'hsl(var(--background))',
                border: '1px solid hsl(var(--border))',
                borderRadius: '0.5rem',
              }}
              formatter={(value: number) => [value.toFixed(3), 'Risk Score']}
            />
            <Line
              type="monotone"
              dataKey="riskScore"
              stroke="hsl(var(--primary))"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
