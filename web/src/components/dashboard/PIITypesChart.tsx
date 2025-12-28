import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts';

interface PIITypeData {
  entity_type: string;
  count: number;
}

interface PIITypesChartProps {
  data: PIITypeData[];
}

const PII_COLORS: Record<string, string> = {
  'credit_card': '#ef4444',      // red-500
  'ssn': '#f97316',              // orange-500
  'phone': '#eab308',            // yellow-500
  'email': '#3b82f6',            // blue-500
  'ip_address': '#8b5cf6',       // violet-500
  'person': '#ec4899',           // pink-500
  'location': '#14b8a6',         // teal-500
  'organization': '#06b6d4',     // cyan-500
};

const DEFAULT_COLOR = '#6b7280'; // gray-500

export function PIITypesChart({ data }: PIITypesChartProps) {
  const chartData = data.map((item) => ({
    name: item.entity_type.replace(/_/g, ' ').toUpperCase(),
    value: item.count,
    color: PII_COLORS[item.entity_type] || DEFAULT_COLOR,
  })).filter(item => item.value > 0);

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

    if (percent < 0.05) return null;

    return (
      <text
        x={x}
        y={y}
        fill="white"
        textAnchor={x > cx ? 'start' : 'end'}
        dominantBaseline="central"
        className="text-xs font-semibold"
      >
        {`${(percent * 100).toFixed(0)}%`}
      </text>
    );
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>PII Types Detected</CardTitle>
        <CardDescription>
          Breakdown by PII category
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={220}>
          <PieChart>
            <Pie
              data={chartData}
              cx="50%"
              cy="50%"
              labelLine={false}
              label={renderCustomizedLabel}
              outerRadius={80}
              innerRadius={50}
              fill="#8884d8"
              dataKey="value"
              paddingAngle={2}
            >
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{
                backgroundColor: 'hsl(var(--background))',
                border: '1px solid hsl(var(--border))',
                borderRadius: '0.5rem',
              }}
              formatter={(value: number | undefined) => [value || 0, 'Detections']}
            />
            <Legend
              verticalAlign="bottom"
              height={36}
              iconType="circle"
              wrapperStyle={{ fontSize: '11px' }}
            />
          </PieChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
