import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../api/client';

interface OrgRiskData {
  orgId: string;
  orgName: string;
  overallScore: number;
  threatScore: number;
  vulnerabilityScore: number;
  complianceScore: number;
  trend: 'improving' | 'stable' | 'worsening';
}

const fetchOrgRiskScores = async (): Promise<OrgRiskData[]> => {
  const response = await apiClient.get<OrgRiskData[]>('/dashboard/risk-scores');
  return response.data;
};

export const RiskHeatmap: React.FC = () => {
  const { data: riskData = [] } = useQuery({
    queryKey: ['riskScores'],
    queryFn: fetchOrgRiskScores,
  });

  const getColorForScore = (score: number) => {
    if (score < 30) return '#22c55e'; // Green
    if (score < 50) return '#eab308'; // Yellow
    if (score < 70) return '#f97316'; // Orange
    return '#ef4444'; // Red
  };

  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'improving': return '📈';
      case 'worsening': return '📉';
      default: return '➡️';
    }
  };

  return (
    <div className="risk-heatmap">
      <h3>Organization Risk Scores</h3>

      <div className="heatmap-grid">
         {riskData.map((org: OrgRiskData) => (
          <div
            key={org.orgId}
            className="risk-cell"
            style={{
              backgroundColor: getColorForScore(org.overallScore),
              opacity: 0.7 + (org.overallScore / 300)
            }}
          >
            <div className="cell-header">
              <span className="org-name">{org.orgName}</span>
              <span className="trend-icon">{getTrendIcon(org.trend)}</span>
            </div>

            <div className="overall-score">
              {org.overallScore.toFixed(0)}
            </div>

            <div className="sub-scores">
              <div className="sub-score">
                <span>Threat</span>
                <span>{org.threatScore.toFixed(0)}</span>
              </div>
              <div className="sub-score">
                <span>Vuln</span>
                <span>{org.vulnerabilityScore.toFixed(0)}</span>
              </div>
              <div className="sub-score">
                <span>Compliance</span>
                <span>{org.complianceScore.toFixed(0)}</span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Legend */}
      <div className="heatmap-legend">
        <span className="legend-label">Low Risk</span>
        <div className="legend-gradient" />
        <span className="legend-label">High Risk</span>
      </div>
    </div>
  );
};