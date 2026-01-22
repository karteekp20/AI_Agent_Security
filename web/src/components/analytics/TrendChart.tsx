import React from 'react';
import {
  ComposedChart, Line, XAxis, YAxis, Tooltip,
  ResponsiveContainer, Legend, Brush
} from 'recharts';

interface TrendChartProps {
  data: Array<{
    timestamp: string;
    value: number;
    anomaly?: boolean;
    trend?: 'up' | 'down' | 'stable';
  }>;
  metric: string;
  showAnomaly?: boolean;
  showTrend?: boolean;
}

const calculateTrendLine = (data: Array<{ timestamp: string; value: number }>) => {
  if (data.length < 2) return data;
  const n = data.length;
  const sumX = n * (n - 1) / 2;
  const sumY = data.reduce((acc, d) => acc + d.value, 0);
  const sumXY = data.reduce((acc, d, i) => acc + i * d.value, 0);
  const sumX2 = n * (n - 1) * (2 * n - 1) / 6;
  const slope = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX);
  const intercept = (sumY - slope * sumX) / n;
  
  return data.map((d, i) => ({
    ...d,
    trend: slope * i + intercept
  }));
};

export const TrendChart: React.FC<TrendChartProps> = ({
  data,
  metric,
  showAnomaly = true,
  showTrend = true,
}) => {
  // Calculate trend line
  const trendData = calculateTrendLine(data);

  return (
    <div className="trend-chart">
      <ResponsiveContainer width="100%" height={400}>
        <ComposedChart data={data}>
          <XAxis
            dataKey="timestamp"
            tickFormatter={(t) => new Date(t).toLocaleDateString()}
          />
          <YAxis />
          <Tooltip
            contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #4b5563' }}
            labelFormatter={(value) => new Date(value).toLocaleDateString()}
          />
          <Legend />

          {/* Main value line */}
          <Line
            type="monotone"
            dataKey="value"
            stroke="#3b82f6"
            strokeWidth={2}
            dot={false}
            name={metric}
          />

          {/* Trend line */}
          {showTrend && (
            <Line
              type="monotone"
              data={trendData}
              dataKey="trend"
              stroke="#9ca3af"
              strokeDasharray="5 5"
              dot={false}
              name="Trend"
            />
          )}

          {/* Anomaly markers */}
          {showAnomaly && (
            <Line
              type="monotone"
              dataKey={(d) => d.anomaly ? d.value : null}
              stroke="#ef4444"
              strokeWidth={0}
              dot={{ r: 6, fill: '#ef4444' }}
              name="Anomalies"
            />
          )}

          {/* Brush for zooming */}
          <Brush
            dataKey="timestamp"
            height={30}
            stroke="#3b82f6"
            tickFormatter={(t) => new Date(t).toLocaleDateString()}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
};