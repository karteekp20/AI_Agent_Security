import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../api/client';

interface BehaviorEvent {
  id: string;
  timestamp: string;
  eventType: 'request' | 'blocked' | 'anomaly' | 'pii';
  riskScore: number;
  deviation?: number;
  details: string;
}

interface BehaviorTimelineProps {
  userId: string;
  orgId: string;
  timeRange: string;
  userName?: string;
  userEmail?: string;
}

const fetchBehaviorEvents = async (
  userId: string,
  orgId: string,
  timeRange: string
): Promise<BehaviorEvent[]> => {
  try {
    const response = await apiClient.get<BehaviorEvent[]>(
      `/audit/user-events`,
      { params: { user_id: userId, org_id: orgId, time_range: timeRange } }
    );
    return response.data;
  } catch (error) {
    // Return mock data if endpoint not available
    return [
      {
        id: '1',
        timestamp: new Date(Date.now() - 3600000).toISOString(),
        eventType: 'blocked',
        riskScore: 0.95,
        details: 'SQL injection attempt detected in user input',
        deviation: 0.8,
      },
      {
        id: '2',
        timestamp: new Date(Date.now() - 1800000).toISOString(),
        eventType: 'pii',
        riskScore: 0.72,
        details: 'PII (credit card) detected and redacted',
        deviation: 0.5,
      },
      {
        id: '3',
        timestamp: new Date(Date.now() - 900000).toISOString(),
        eventType: 'request',
        riskScore: 0.15,
        details: 'Normal user request processed',
        deviation: 0.05,
      },
    ];
  }
};

const getRiskLevel = (score: number): string => {
  if (score < 0.3) return 'low';
  if (score < 0.6) return 'medium';
  if (score < 0.8) return 'high';
  return 'critical';
};

export const BehaviorTimeline: React.FC<BehaviorTimelineProps> = ({
  userId,
  orgId,
  timeRange,
  userName,
  userEmail,
}) => {
  const { data: events = [] } = useQuery({
    queryKey: ['behavior', userId, timeRange],
    queryFn: () => fetchBehaviorEvents(userId, orgId, timeRange),
  });

  const getEventIcon = (type: string) => {
    switch (type) {
      case 'request': return '📝';
      case 'blocked': return '🚫';
      case 'anomaly': return '⚠️';
      case 'pii': return '🔒';
      default: return '•';
    }
  };

  const getEventColor = (event: BehaviorEvent) => {
    if (event.eventType === 'blocked') return 'bg-red-100 border-red-500';
    if (event.eventType === 'anomaly') return 'bg-yellow-100 border-yellow-500';
    if (event.riskScore > 0.7) return 'bg-orange-100 border-orange-500';
    return 'bg-gray-50 border-gray-200';
  };

  return (
    <div className="behavior-timeline">
      <div className="timeline-header">
        <h3>User Behavior Timeline</h3>
        <div className="user-info">
          {userName ? (
            <>
              <span className="user-name">{userName}</span>
              {userEmail && <span className="user-email">{userEmail}</span>}
            </>
          ) : (
            <span className="user-id">{userId}</span>
          )}
        </div>
      </div>

      <div className="timeline-container">
        {events?.map((event: BehaviorEvent, index: number) => (
          <div
            key={event.id}
            className={`timeline-event ${getEventColor(event)}`}
          >
            <div className="event-marker">
              <span className="event-icon">{getEventIcon(event.eventType)}</span>
              {index < (events.length - 1) && <div className="connector-line" />}
            </div>

            <div className="event-content">
              <div className="event-header">
                <span className="event-time">
                  {new Date(event.timestamp).toLocaleString()}
                </span>
                <span className={`risk-badge risk-${getRiskLevel(event.riskScore)}`}>
                  Risk: {(event.riskScore * 100).toFixed(0)}%
                </span>
              </div>

              <p className="event-details">{event.details}</p>

              {event.deviation !== undefined && event.deviation > 0.3 && (
                <div className="deviation-indicator">
                  ⚡ {(event.deviation * 100).toFixed(0)}% deviation from baseline
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};