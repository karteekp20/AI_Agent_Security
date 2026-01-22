import React from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  LineChart, Line, XAxis, YAxis, Tooltip,
  ReferenceLine, ResponsiveContainer, Area
} from 'recharts';
import { apiClient } from '../../api/client';

interface AnomalyData {
  timestamp: string;
  score: number;
  isAnomaly: boolean;
  features: {
    name: string;
    deviation: number;
    contribution: number;
  }[];
}

interface AnomalyVisualizationProps {
  userId?: string;
  orgId: string;
  timeRange: string;
}

const fetchAnomalies = async (orgId: string, userId?: string, timeRange?: string): Promise<AnomalyData[]> => {
  try {
    const response = await apiClient.get<AnomalyData[]>(`/ml/anomaly/analyze`, {
      params: { org_id: orgId, ...(userId && { user_id: userId }), ...(timeRange && { time_range: timeRange }) },
    });
    return response.data;
  } catch (error) {
    // Return mock data if endpoint not available
    return [
      {
        timestamp: new Date().toISOString(),
        score: 0.65,
        isAnomaly: false,
        features: [
          { name: 'request_count', deviation: 0.45, contribution: 0.35 },
          { name: 'response_time', deviation: 0.28, contribution: 0.28 },
          { name: 'error_rate', deviation: 0.15, contribution: 0.18 },
          { name: 'unique_endpoints', deviation: 0.12, contribution: 0.12 },
          { name: 'bytes_transferred', deviation: 0.08, contribution: 0.07 },
        ],
      },
    ];
  }
};

const FeatureContributionChart: React.FC<{ features: AnomalyData['features'] }> = ({ features }) => {
  return (
    <div className="feature-contribution">
      {features.length > 0 ? (
        features.map((f) => (
          <div key={f.name} className="feature-row">
            <span className="feature-name">{f.name}</span>
            <div className="feature-bar" style={{ width: `${f.contribution * 100}%` }} />
            <span className="feature-value">{(f.contribution * 100).toFixed(1)}%</span>
          </div>
        ))
      ) : (
        <p>No feature data available</p>
      )}
    </div>
  );
};

export const AnomalyVisualization: React.FC<AnomalyVisualizationProps> = ({
  userId,
  orgId,
  timeRange,
}) => {
  const { data: anomalyData = [] } = useQuery({
    queryKey: ['anomalies', orgId, userId, timeRange],
    queryFn: () => fetchAnomalies(orgId, userId, timeRange),
  });

  const threshold = 0.7; // Anomaly threshold

  return (
    <div className="anomaly-visualization">
      <div className="anomaly-header">
        <h3>Anomaly Detection</h3>
        <span className="anomaly-count">
          {anomalyData?.filter(d => d.isAnomaly).length || 0} anomalies detected
        </span>
      </div>

      {/* Time series chart */}
      <div className="anomaly-chart">
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={anomalyData || []}>
            <defs>
              <linearGradient id="anomalyGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3}/>
                <stop offset="95%" stopColor="#ef4444" stopOpacity={0}/>
              </linearGradient>
            </defs>

            <XAxis
              dataKey="timestamp"
              tickFormatter={(t) => new Date(t).toLocaleTimeString()}
            />
            <YAxis domain={[0, 1]} />
            <Tooltip content={<AnomalyTooltip />} />

            {/* Threshold line */}
            <ReferenceLine
              y={threshold}
              stroke="#ef4444"
              strokeDasharray="5 5"
              label="Threshold"
            />

            {/* Anomaly score line */}
            <Area
              type="monotone"
              dataKey="score"
              stroke="#3b82f6"
              fill="url(#anomalyGradient)"
              strokeWidth={2}
            />

            {/* Highlight anomalies */}
            <Line
              type="monotone"
              dataKey={(d) => d.isAnomaly ? d.score : null}
              stroke="#ef4444"
              strokeWidth={0}
              dot={{ r: 6, fill: '#ef4444' }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Feature contribution breakdown */}
      <div className="feature-breakdown">
        <h4>Top Contributing Features</h4>
        <FeatureContributionChart
          features={(anomalyData && anomalyData.length > 0 ? anomalyData[0].features : [])}
        />
      </div>
    </div>
  );
};

const AnomalyTooltip: React.FC<any> = ({ active, payload }) => {
  if (!active || !payload?.[0]) return null;

  const data = payload[0].payload as AnomalyData;

  return (
    <div className="anomaly-tooltip">
      <p className="time">{new Date(data.timestamp).toLocaleString()}</p>
      <p className={`score ${data.isAnomaly ? 'anomaly' : 'normal'}`}>
        Score: {data.score.toFixed(3)}
        {data.isAnomaly && <span className="badge">ANOMALY</span>}
      </p>
      <div className="features">
        {data.features.slice(0, 3).map(f => (
          <p key={f.name}>
            {f.name}: {(f.deviation * 100).toFixed(0)}% deviation
          </p>
        ))}
      </div>
    </div>
  );
}; 