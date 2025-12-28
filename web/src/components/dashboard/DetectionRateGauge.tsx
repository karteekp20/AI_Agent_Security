import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts';

interface DetectionRateGaugeProps {
  totalRequests: number;
  threatsBlocked: number;
}

export function DetectionRateGauge({ totalRequests, threatsBlocked }: DetectionRateGaugeProps) {
  const detectionRate = totalRequests > 0 ? (threatsBlocked / totalRequests) * 100 : 0;

  const data = [
    { name: 'Blocked', value: threatsBlocked },
    { name: 'Clean', value: totalRequests - threatsBlocked },
  ];

  const getColor = (rate: number) => {
    if (rate < 10) return '#22c55e'; // green - low threat
    if (rate < 30) return '#eab308'; // yellow - moderate
    if (rate < 50) return '#f97316'; // orange - concerning
    return '#ef4444'; // red - high threat
  };

  const gaugeColor = getColor(detectionRate);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Detection Rate</CardTitle>
        <CardDescription>
          Percentage of requests blocked
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="flex flex-col items-center justify-center">
          <ResponsiveContainer width="100%" height={180}>
            <PieChart>
              <Pie
                data={data}
                cx="50%"
                cy="50%"
                startAngle={180}
                endAngle={0}
                innerRadius={60}
                outerRadius={80}
                dataKey="value"
                stroke="none"
              >
                <Cell fill={gaugeColor} />
                <Cell fill="hsl(var(--muted))" />
              </Pie>
            </PieChart>
          </ResponsiveContainer>
          <div className="text-center -mt-16 mb-8">
            <div className="text-3xl font-bold" style={{ color: gaugeColor }}>
              {detectionRate.toFixed(1)}%
            </div>
            <div className="text-xs text-muted-foreground mt-1">
              {threatsBlocked.toLocaleString()} / {totalRequests.toLocaleString()} blocked
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4 w-full text-center text-xs">
            <div>
              <div className="font-semibold text-green-600 dark:text-green-400">
                {totalRequests - threatsBlocked}
              </div>
              <div className="text-muted-foreground">Clean</div>
            </div>
            <div>
              <div className="font-semibold text-red-600 dark:text-red-400">
                {threatsBlocked}
              </div>
              <div className="text-muted-foreground">Blocked</div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
