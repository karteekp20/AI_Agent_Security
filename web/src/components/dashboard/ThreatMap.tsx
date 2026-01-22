import React, { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../api/client';

interface ThreatEvent {
  id: string;
  timestamp: string;
  type: 'pii' | 'injection' | 'anomaly' | 'content';
  severity: 'low' | 'medium' | 'high' | 'critical';
  location?: { lat: number; lng: number };
  blocked: boolean;
  details: Record<string, any>;
}

interface ThreatMapProps {
  orgId: string;
  timeRange: '1h' | '24h' | '7d';
  onThreatClick?: (threat: ThreatEvent) => void;
}

const fetchThreats = async (orgId: string, timeRange: string): Promise<ThreatEvent[]> => {
  const response = await apiClient.get<ThreatEvent[]>('/dashboard/threats', {
    params: { org_id: orgId, time_range: timeRange },
  });
  return response.data;
};

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000';

const ThreatListItem: React.FC<{ threat: ThreatEvent; onClick?: () => void }> = ({
  threat,
  onClick,
}) => {
  const severityIcons: Record<string, string> = {
    low: '🟢',
    medium: '🟡',
    high: '🟠',
    critical: '🔴',
  };
  
  return (
    <div className="threat-item" onClick={onClick}>
      <span className="severity-icon">{severityIcons[threat.severity] || '•'}</span>
      <div className="threat-info">
        <span className="threat-type">{threat.type}</span>
        <span className="threat-time">
          {new Date(threat.timestamp).toLocaleTimeString()}
        </span>
      </div>
      {threat.blocked && <span className="blocked-badge">Blocked</span>}
    </div>
  );
};

export const ThreatMap: React.FC<ThreatMapProps> = ({
  orgId,
  timeRange,
  onThreatClick,
}) => {
  const [liveThreats, setLiveThreats] = useState<ThreatEvent[]>([]);

  // Fetch historical threats
  const { data: threats = [] } = useQuery({
    queryKey: ['threats', orgId, timeRange],
    queryFn: () => fetchThreats(orgId, timeRange),
    refetchInterval: 30000, // Refresh every 30s
  });

  // WebSocket for real-time updates
  useEffect(() => {
    const ws = new WebSocket(`${WS_URL}/threats/${orgId}`);

    ws.onmessage = (event) => {
      const threat = JSON.parse(event.data) as ThreatEvent;
      setLiveThreats(prev => [threat, ...prev].slice(0, 50));
    };

    return () => ws.close();
  }, [orgId]);

  const severityColors: Record<string, string> = {
    low: '#22c55e',
    medium: '#eab308',
    high: '#f97316',
    critical: '#ef4444',
  };

  return (
    <div className="threat-map-container">
      <div className="threat-map-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h3 style={{ margin: 0 }}>Live Threat Activity</h3>
        <div className="threat-legend" style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
          {Object.entries(severityColors).map(([severity, color]) => (
            <span key={severity} className="legend-item" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.5rem 0.75rem', backgroundColor: '#f5f5f5', borderRadius: '4px', fontSize: '0.875rem', fontWeight: '500' }}>
              <span className="dot" style={{ backgroundColor: color, width: '12px', height: '12px', borderRadius: '50%', flexShrink: 0 }} />
              <span style={{ textTransform: 'capitalize' }}>{severity}</span>
            </span>
          ))}
        </div>
      </div>

      <div className="threat-map-visualization">
        {/* World map or abstract visualization */}
        <svg viewBox="0 0 1000 500" className="map-svg">
          {/* Map paths would go here */}

          {/* Threat markers */}
          {[...liveThreats, ...(threats || [])].map((threat: ThreatEvent) => (
            <circle
              key={threat.id}
              cx={threat.location?.lng || Math.random() * 1000}
              cy={threat.location?.lat || Math.random() * 500}
              r={threat.severity === 'critical' ? 12 : 8}
              fill={severityColors[threat.severity as keyof typeof severityColors]}
              className="threat-marker"
              onClick={() => onThreatClick?.(threat)}
              style={{ cursor: 'pointer' }}
            />
          ))}
        </svg>
      </div>

      {/* Recent threats list */}
      <div className="recent-threats-list">
        <h4>Recent Activity</h4>
        {liveThreats.slice(0, 10).map((threat: ThreatEvent) => (
          <ThreatListItem
            key={threat.id}
            threat={threat}
            onClick={() => onThreatClick?.(threat)}
          />
        ))}
      </div>
    </div>
  );
};