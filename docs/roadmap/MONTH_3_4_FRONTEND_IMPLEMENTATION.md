# Month 3-4: Frontend Implementation Guide

**Objective:** Detailed frontend implementation for advanced security features
**Timeline:** September-October 2025
**Target:** ~600 lines of implementation specifications

---

## Table of Contents

1. [Advanced Threat Dashboard](#1-advanced-threat-dashboard)
2. [Policy Management UI](#2-policy-management-ui)
3. [Security Analytics Visualizations](#3-security-analytics-visualizations)
4. [Integration Management UI](#4-integration-management-ui)
5. [Component Specifications](#5-component-specifications)
6. [State Management](#6-state-management)
7. [API Integration](#7-api-integration)

---

## 1. Advanced Threat Dashboard

### 1.1 Real-time Threat Map

A visual representation of threats across the organization, updated in real-time.

```tsx
// components/dashboard/ThreatMap.tsx
import React, { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';

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

export const ThreatMap: React.FC<ThreatMapProps> = ({
  orgId,
  timeRange,
  onThreatClick,
}) => {
  const [liveThreats, setLiveThreats] = useState<ThreatEvent[]>([]);

  // Fetch historical threats
  const { data: threats, isLoading } = useQuery({
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

  const severityColors = {
    low: '#22c55e',
    medium: '#eab308',
    high: '#f97316',
    critical: '#ef4444',
  };

  return (
    <div className="threat-map-container">
      <div className="threat-map-header">
        <h3>Live Threat Activity</h3>
        <div className="threat-legend">
          {Object.entries(severityColors).map(([severity, color]) => (
            <span key={severity} className="legend-item">
              <span className="dot" style={{ backgroundColor: color }} />
              {severity}
            </span>
          ))}
        </div>
      </div>

      <div className="threat-map-visualization">
        {/* World map or abstract visualization */}
        <svg viewBox="0 0 1000 500" className="map-svg">
          {/* Map paths would go here */}

          {/* Threat markers */}
          <AnimatePresence>
            {[...liveThreats, ...(threats || [])].map((threat) => (
              <motion.circle
                key={threat.id}
                initial={{ scale: 0, opacity: 0 }}
                animate={{ scale: 1, opacity: 0.8 }}
                exit={{ scale: 0, opacity: 0 }}
                cx={threat.location?.lng || Math.random() * 1000}
                cy={threat.location?.lat || Math.random() * 500}
                r={threat.severity === 'critical' ? 12 : 8}
                fill={severityColors[threat.severity]}
                className="threat-marker"
                onClick={() => onThreatClick?.(threat)}
              />
            ))}
          </AnimatePresence>
        </svg>
      </div>

      {/* Recent threats list */}
      <div className="recent-threats-list">
        <h4>Recent Activity</h4>
        {liveThreats.slice(0, 10).map((threat) => (
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
```

### 1.2 Anomaly Visualization

Display ML-detected anomalies with explanations.

```tsx
// components/dashboard/AnomalyVisualization.tsx
import React from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  LineChart, Line, XAxis, YAxis, Tooltip,
  ReferenceLine, ResponsiveContainer, Area
} from 'recharts';

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

export const AnomalyVisualization: React.FC<AnomalyVisualizationProps> = ({
  userId,
  orgId,
  timeRange,
}) => {
  const { data: anomalyData, isLoading } = useQuery({
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
          <LineChart data={anomalyData}>
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
          features={anomalyData?.[0]?.features || []}
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
```

### 1.3 Behavior Timeline

Visualize user behavior over time with deviations highlighted.

```tsx
// components/dashboard/BehaviorTimeline.tsx
import React from 'react';
import { useQuery } from '@tanstack/react-query';

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
}

export const BehaviorTimeline: React.FC<BehaviorTimelineProps> = ({
  userId,
  orgId,
  timeRange,
}) => {
  const { data: events } = useQuery({
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
        <span className="user-id">User: {userId}</span>
      </div>

      <div className="timeline-container">
        {events?.map((event, index) => (
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
```

---

## 2. Policy Management UI

### 2.1 Version History Viewer

```tsx
// components/policies/VersionHistory.tsx
import React, { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { formatDistanceToNow } from 'date-fns';

interface PolicyVersion {
  policyId: string;
  version: number;
  status: 'draft' | 'testing' | 'active' | 'archived';
  createdAt: string;
  createdBy: string;
  commitMessage: string;
}

interface VersionHistoryProps {
  policyId: string;
  onVersionSelect: (version: PolicyVersion) => void;
  onRollback: (targetVersion: number) => void;
}

export const VersionHistory: React.FC<VersionHistoryProps> = ({
  policyId,
  onVersionSelect,
  onRollback,
}) => {
  const [selectedVersions, setSelectedVersions] = useState<string[]>([]);

  const { data: versions, isLoading } = useQuery({
    queryKey: ['policyVersions', policyId],
    queryFn: () => fetchPolicyVersions(policyId),
  });

  const rollbackMutation = useMutation({
    mutationFn: (targetVersion: number) =>
      rollbackPolicy(policyId, targetVersion),
    onSuccess: () => {
      // Invalidate queries to refresh
    },
  });

  const handleCompare = () => {
    if (selectedVersions.length === 2) {
      // Navigate to diff view
      window.location.href =
        `/policies/diff?a=${selectedVersions[0]}&b=${selectedVersions[1]}`;
    }
  };

  const statusColors = {
    draft: 'bg-gray-100 text-gray-700',
    testing: 'bg-yellow-100 text-yellow-700',
    active: 'bg-green-100 text-green-700',
    archived: 'bg-red-100 text-red-700',
  };

  return (
    <div className="version-history">
      <div className="version-header">
        <h3>Version History</h3>
        {selectedVersions.length === 2 && (
          <button onClick={handleCompare} className="btn-compare">
            Compare Selected
          </button>
        )}
      </div>

      <div className="version-list">
        {versions?.map((version, index) => (
          <div
            key={version.policyId}
            className={`version-item ${
              selectedVersions.includes(version.policyId) ? 'selected' : ''
            }`}
          >
            <input
              type="checkbox"
              checked={selectedVersions.includes(version.policyId)}
              onChange={(e) => {
                if (e.target.checked && selectedVersions.length < 2) {
                  setSelectedVersions([...selectedVersions, version.policyId]);
                } else {
                  setSelectedVersions(
                    selectedVersions.filter(id => id !== version.policyId)
                  );
                }
              }}
            />

            <div className="version-info" onClick={() => onVersionSelect(version)}>
              <div className="version-number">
                v{version.version}
                {index === 0 && <span className="current-badge">Current</span>}
              </div>

              <span className={`status-badge ${statusColors[version.status]}`}>
                {version.status}
              </span>

              <div className="version-meta">
                <span className="commit-message">{version.commitMessage}</span>
                <span className="timestamp">
                  {formatDistanceToNow(new Date(version.createdAt))} ago
                </span>
                <span className="author">by {version.createdBy}</span>
              </div>
            </div>

            {version.status !== 'active' && (
              <button
                className="btn-rollback"
                onClick={() => onRollback(version.version)}
                disabled={rollbackMutation.isPending}
              >
                Rollback
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
```

### 2.2 A/B Test Configuration Wizard

```tsx
// components/policies/ABTestWizard.tsx
import React, { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';

interface ABTestConfig {
  controlPolicyId: string;
  variantPolicyId: string;
  trafficPercentage: number;
  durationDays: number;
  targetingRules?: {
    userIds?: string[];
    workspaces?: string[];
  };
}

interface ABTestWizardProps {
  controlPolicyId: string;
  onComplete: () => void;
  onCancel: () => void;
}

export const ABTestWizard: React.FC<ABTestWizardProps> = ({
  controlPolicyId,
  onComplete,
  onCancel,
}) => {
  const [step, setStep] = useState(1);
  const [config, setConfig] = useState<ABTestConfig>({
    controlPolicyId,
    variantPolicyId: '',
    trafficPercentage: 10,
    durationDays: 7,
  });

  // Fetch available variant policies
  const { data: policies } = useQuery({
    queryKey: ['policies', 'variants'],
    queryFn: () => fetchDraftPolicies(),
  });

  const createTestMutation = useMutation({
    mutationFn: (config: ABTestConfig) => createABTest(config),
    onSuccess: onComplete,
  });

  const steps = [
    { title: 'Select Variant', component: StepSelectVariant },
    { title: 'Traffic Split', component: StepTrafficSplit },
    { title: 'Duration & Targeting', component: StepDurationTargeting },
    { title: 'Review', component: StepReview },
  ];

  const CurrentStepComponent = steps[step - 1].component;

  return (
    <div className="ab-test-wizard">
      {/* Progress indicator */}
      <div className="wizard-progress">
        {steps.map((s, i) => (
          <div
            key={i}
            className={`step ${i + 1 <= step ? 'active' : ''} ${
              i + 1 < step ? 'completed' : ''
            }`}
          >
            <span className="step-number">{i + 1}</span>
            <span className="step-title">{s.title}</span>
          </div>
        ))}
      </div>

      {/* Current step content */}
      <div className="wizard-content">
        <CurrentStepComponent
          config={config}
          setConfig={setConfig}
          policies={policies}
        />
      </div>

      {/* Navigation buttons */}
      <div className="wizard-actions">
        <button onClick={onCancel} className="btn-cancel">
          Cancel
        </button>

        {step > 1 && (
          <button onClick={() => setStep(step - 1)} className="btn-back">
            Back
          </button>
        )}

        {step < steps.length ? (
          <button
            onClick={() => setStep(step + 1)}
            className="btn-next"
            disabled={step === 1 && !config.variantPolicyId}
          >
            Next
          </button>
        ) : (
          <button
            onClick={() => createTestMutation.mutate(config)}
            className="btn-create"
            disabled={createTestMutation.isPending}
          >
            {createTestMutation.isPending ? 'Creating...' : 'Create A/B Test'}
          </button>
        )}
      </div>
    </div>
  );
};

// Step components
const StepSelectVariant: React.FC<any> = ({ config, setConfig, policies }) => (
  <div className="step-select-variant">
    <h4>Select the variant policy to test</h4>
    <p className="help-text">
      Choose a draft policy to test against your current active policy.
    </p>

    <div className="policy-grid">
      {policies?.map((policy: any) => (
        <div
          key={policy.policyId}
          className={`policy-card ${
            config.variantPolicyId === policy.policyId ? 'selected' : ''
          }`}
          onClick={() => setConfig({ ...config, variantPolicyId: policy.policyId })}
        >
          <h5>{policy.policyName}</h5>
          <p>{policy.description}</p>
          <span className="policy-type">{policy.policyType}</span>
        </div>
      ))}
    </div>
  </div>
);

const StepTrafficSplit: React.FC<any> = ({ config, setConfig }) => (
  <div className="step-traffic-split">
    <h4>Configure traffic split</h4>
    <p className="help-text">
      Percentage of traffic to send to the variant policy.
    </p>

    <div className="traffic-slider">
      <input
        type="range"
        min={1}
        max={50}
        value={config.trafficPercentage}
        onChange={(e) => setConfig({
          ...config,
          trafficPercentage: parseInt(e.target.value)
        })}
      />
      <div className="traffic-labels">
        <span>Control: {100 - config.trafficPercentage}%</span>
        <span>Variant: {config.trafficPercentage}%</span>
      </div>
    </div>

    <div className="traffic-preview">
      <div
        className="control-bar"
        style={{ width: `${100 - config.trafficPercentage}%` }}
      />
      <div
        className="variant-bar"
        style={{ width: `${config.trafficPercentage}%` }}
      />
    </div>
  </div>
);

const StepDurationTargeting: React.FC<any> = ({ config, setConfig }) => (
  <div className="step-duration">
    <h4>Set test duration</h4>

    <div className="duration-options">
      {[3, 7, 14, 30].map((days) => (
        <button
          key={days}
          className={`duration-btn ${config.durationDays === days ? 'active' : ''}`}
          onClick={() => setConfig({ ...config, durationDays: days })}
        >
          {days} days
        </button>
      ))}
    </div>

    <div className="targeting-section">
      <h4>Optional: Target specific users</h4>
      <textarea
        placeholder="Enter user IDs (one per line) or leave empty for all users"
        onChange={(e) => {
          const userIds = e.target.value.split('\n').filter(Boolean);
          setConfig({
            ...config,
            targetingRules: userIds.length ? { userIds } : undefined,
          });
        }}
      />
    </div>
  </div>
);

const StepReview: React.FC<any> = ({ config }) => (
  <div className="step-review">
    <h4>Review your A/B test configuration</h4>

    <dl className="config-summary">
      <dt>Control Policy</dt>
      <dd>{config.controlPolicyId}</dd>

      <dt>Variant Policy</dt>
      <dd>{config.variantPolicyId}</dd>

      <dt>Traffic Split</dt>
      <dd>{100 - config.trafficPercentage}% / {config.trafficPercentage}%</dd>

      <dt>Duration</dt>
      <dd>{config.durationDays} days</dd>

      <dt>Targeting</dt>
      <dd>
        {config.targetingRules?.userIds?.length
          ? `${config.targetingRules.userIds.length} specific users`
          : 'All users'}
      </dd>
    </dl>
  </div>
);
```

### 2.3 DSL Editor with Syntax Highlighting

```tsx
// components/policies/DSLEditor.tsx
import React, { useCallback, useMemo } from 'react';
import CodeMirror from '@uiw/react-codemirror';
import { StreamLanguage } from '@codemirror/language';
import { tags as t } from '@lezer/highlight';
import { createTheme } from '@uiw/codemirror-themes';

// Custom language definition for Sentinel DSL
const sentinelDSL = StreamLanguage.define({
  token(stream) {
    // Keywords
    if (stream.match(/\b(policy|when|then|and|or|not|action|block|allow|log|alert)\b/)) {
      return 'keyword';
    }
    // Objects
    if (stream.match(/\b(input|output|context|user)\b/)) {
      return 'variableName';
    }
    // Methods
    if (stream.match(/\.\w+\s*\(/)) {
      stream.backUp(1);
      return 'function';
    }
    // Strings
    if (stream.match(/"[^"]*"/)) {
      return 'string';
    }
    // Numbers
    if (stream.match(/\d+(\.\d+)?/)) {
      return 'number';
    }
    // Comments
    if (stream.match(/#.*/)) {
      return 'comment';
    }
    // Operators
    if (stream.match(/[><=!]+/)) {
      return 'operator';
    }
    // Brackets
    if (stream.match(/[{}()]/)) {
      return 'bracket';
    }
    // Skip other characters
    stream.next();
    return null;
  },
});

// Custom theme
const sentinelTheme = createTheme({
  theme: 'dark',
  settings: {
    background: '#1e1e2e',
    foreground: '#cdd6f4',
    selection: '#45475a',
    selectionMatch: '#45475a',
    lineHighlight: '#313244',
  },
  styles: [
    { tag: t.keyword, color: '#cba6f7' },
    { tag: t.variableName, color: '#89b4fa' },
    { tag: t.function(t.variableName), color: '#f9e2af' },
    { tag: t.string, color: '#a6e3a1' },
    { tag: t.number, color: '#fab387' },
    { tag: t.comment, color: '#6c7086' },
    { tag: t.operator, color: '#94e2d5' },
    { tag: t.bracket, color: '#f5c2e7' },
  ],
});

interface DSLEditorProps {
  value: string;
  onChange: (value: string) => void;
  onValidate?: (errors: string[]) => void;
  readOnly?: boolean;
}

export const DSLEditor: React.FC<DSLEditorProps> = ({
  value,
  onChange,
  onValidate,
  readOnly = false,
}) => {
  // Validate DSL syntax
  const validateDSL = useCallback(async (code: string) => {
    try {
      const response = await fetch('/api/v1/policies/dsl/validate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code }),
      });
      const result = await response.json();
      onValidate?.(result.errors || []);
    } catch (e) {
      console.error('Validation error:', e);
    }
  }, [onValidate]);

  // Debounced validation
  const debouncedValidate = useMemo(
    () => debounce(validateDSL, 500),
    [validateDSL]
  );

  const handleChange = useCallback((val: string) => {
    onChange(val);
    debouncedValidate(val);
  }, [onChange, debouncedValidate]);

  return (
    <div className="dsl-editor">
      <div className="editor-toolbar">
        <span className="editor-title">Policy DSL</span>
        <div className="toolbar-actions">
          <button className="btn-format" onClick={() => formatCode(value)}>
            Format
          </button>
          <button className="btn-docs" onClick={() => window.open('/docs/dsl')}>
            Documentation
          </button>
        </div>
      </div>

      <CodeMirror
        value={value}
        height="400px"
        theme={sentinelTheme}
        extensions={[sentinelDSL]}
        onChange={handleChange}
        readOnly={readOnly}
        basicSetup={{
          lineNumbers: true,
          highlightActiveLineGutter: true,
          highlightActiveLine: true,
          bracketMatching: true,
          autocompletion: true,
        }}
      />

      {/* Example snippets */}
      <div className="dsl-snippets">
        <h5>Quick Snippets</h5>
        <div className="snippet-buttons">
          <button onClick={() => insertSnippet('pii-block')}>
            Block PII
          </button>
          <button onClick={() => insertSnippet('injection-detect')}>
            Detect Injection
          </button>
          <button onClick={() => insertSnippet('risk-threshold')}>
            Risk Threshold
          </button>
        </div>
      </div>
    </div>
  );
};

// Helper snippets
const SNIPPETS = {
  'pii-block': `policy "Block PII" {
    when {
        input.contains_pii("ssn", "credit_card")
    }
    then {
        action: block
        reason: "PII detected in input"
    }
}`,
  'injection-detect': `policy "Detect Injection" {
    when {
        input.matches_pattern("ignore.*instructions")
        or input.risk_score > 0.8
    }
    then {
        action: alert
        reason: "Potential injection attempt"
    }
}`,
  'risk-threshold': `policy "High Risk Alert" {
    when {
        input.risk_score > 0.7
        and context.session_anomaly_score > 0.5
    }
    then {
        action: log
        log_level: warning
    }
}`,
};
```

### 2.4 Template Browser

```tsx
// components/policies/TemplateBrowser.tsx
import React, { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';

interface PolicyTemplate {
  templateId: string;
  name: string;
  description: string;
  category: string;
  policyType: string;
  complianceFrameworks?: string[];
  variables: Record<string, VariableSpec>;
}

interface VariableSpec {
  type: 'int' | 'float' | 'enum' | 'multi_select';
  default: any;
  options?: string[];
  min?: number;
  max?: number;
  description?: string;
}

export const TemplateBrowser: React.FC = () => {
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [selectedTemplate, setSelectedTemplate] = useState<PolicyTemplate | null>(null);
  const [variableValues, setVariableValues] = useState<Record<string, any>>({});

  const { data: templates } = useQuery({
    queryKey: ['policyTemplates', selectedCategory],
    queryFn: () => fetchTemplates(selectedCategory),
  });

  const instantiateMutation = useMutation({
    mutationFn: (data: { templateId: string; name: string; variables: Record<string, any> }) =>
      instantiateTemplate(data),
    onSuccess: () => {
      // Navigate to new policy
    },
  });

  const categories = [
    { id: 'pii', name: 'PII Protection', icon: '🔒' },
    { id: 'injection', name: 'Injection Prevention', icon: '🛡️' },
    { id: 'rate_limit', name: 'Rate Limiting', icon: '⚡' },
    { id: 'content_moderation', name: 'Content Safety', icon: '📝' },
    { id: 'compliance', name: 'Compliance', icon: '✅' },
  ];

  return (
    <div className="template-browser">
      {/* Category filter */}
      <div className="category-tabs">
        <button
          className={!selectedCategory ? 'active' : ''}
          onClick={() => setSelectedCategory(null)}
        >
          All
        </button>
        {categories.map((cat) => (
          <button
            key={cat.id}
            className={selectedCategory === cat.id ? 'active' : ''}
            onClick={() => setSelectedCategory(cat.id)}
          >
            {cat.icon} {cat.name}
          </button>
        ))}
      </div>

      <div className="template-content">
        {/* Template grid */}
        <div className="template-grid">
          {templates?.map((template) => (
            <div
              key={template.templateId}
              className={`template-card ${
                selectedTemplate?.templateId === template.templateId ? 'selected' : ''
              }`}
              onClick={() => {
                setSelectedTemplate(template);
                // Initialize variables with defaults
                const defaults: Record<string, any> = {};
                Object.entries(template.variables).forEach(([key, spec]) => {
                  defaults[key] = spec.default;
                });
                setVariableValues(defaults);
              }}
            >
              <h4>{template.name}</h4>
              <p>{template.description}</p>

              <div className="template-meta">
                <span className="category-badge">{template.category}</span>
                {template.complianceFrameworks?.map((fw) => (
                  <span key={fw} className="compliance-badge">{fw}</span>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Configuration panel */}
        {selectedTemplate && (
          <div className="template-config">
            <h3>Configure: {selectedTemplate.name}</h3>

            <div className="variable-form">
              {Object.entries(selectedTemplate.variables).map(([key, spec]) => (
                <div key={key} className="variable-field">
                  <label>{key}</label>
                  {spec.description && <p className="help">{spec.description}</p>}

                  <VariableInput
                    spec={spec}
                    value={variableValues[key]}
                    onChange={(val) => setVariableValues({ ...variableValues, [key]: val })}
                  />
                </div>
              ))}
            </div>

            <div className="config-actions">
              <input
                type="text"
                placeholder="Policy name"
                className="policy-name-input"
              />
              <button
                className="btn-create"
                onClick={() => instantiateMutation.mutate({
                  templateId: selectedTemplate.templateId,
                  name: 'New Policy from Template',
                  variables: variableValues,
                })}
              >
                Create Policy
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

const VariableInput: React.FC<{
  spec: VariableSpec;
  value: any;
  onChange: (value: any) => void;
}> = ({ spec, value, onChange }) => {
  switch (spec.type) {
    case 'int':
    case 'float':
      return (
        <input
          type="number"
          value={value}
          min={spec.min}
          max={spec.max}
          step={spec.type === 'float' ? 0.1 : 1}
          onChange={(e) => onChange(parseFloat(e.target.value))}
        />
      );
    case 'enum':
      return (
        <select value={value} onChange={(e) => onChange(e.target.value)}>
          {spec.options?.map((opt) => (
            <option key={opt} value={opt}>{opt}</option>
          ))}
        </select>
      );
    case 'multi_select':
      return (
        <div className="multi-select">
          {spec.options?.map((opt) => (
            <label key={opt}>
              <input
                type="checkbox"
                checked={value?.includes(opt)}
                onChange={(e) => {
                  if (e.target.checked) {
                    onChange([...(value || []), opt]);
                  } else {
                    onChange((value || []).filter((v: string) => v !== opt));
                  }
                }}
              />
              {opt}
            </label>
          ))}
        </div>
      );
    default:
      return <input type="text" value={value} onChange={(e) => onChange(e.target.value)} />;
  }
};
```

---

## 3. Security Analytics Visualizations

### 3.1 Interactive Trend Charts

```tsx
// components/analytics/TrendChart.tsx
import React, { useState } from 'react';
import {
  ComposedChart, Line, Bar, XAxis, YAxis, Tooltip,
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

export const TrendChart: React.FC<TrendChartProps> = ({
  data,
  metric,
  showAnomaly = true,
  showTrend = true,
}) => {
  const [activeIndex, setActiveIndex] = useState<number | null>(null);

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
          <Tooltip content={<TrendTooltip metric={metric} />} />
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
```

### 3.2 Risk Heatmap

```tsx
// components/analytics/RiskHeatmap.tsx
import React from 'react';
import { useQuery } from '@tanstack/react-query';

interface OrgRiskData {
  orgId: string;
  orgName: string;
  overallScore: number;
  threatScore: number;
  vulnerabilityScore: number;
  complianceScore: number;
  trend: 'improving' | 'stable' | 'worsening';
}

export const RiskHeatmap: React.FC = () => {
  const { data: riskData } = useQuery({
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
        {riskData?.map((org) => (
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
```

---

## 4. Integration Management UI

### 4.1 Webhook Configuration

```tsx
// components/integrations/WebhookConfig.tsx
import React, { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

interface Webhook {
  webhookId: string;
  url: string;
  events: string[];
  enabled: boolean;
  failureCount: number;
  lastTriggered?: string;
}

const EVENT_TYPES = [
  { id: 'threat.detected', name: 'Threat Detected', description: 'When a threat is detected' },
  { id: 'threat.blocked', name: 'Threat Blocked', description: 'When a request is blocked' },
  { id: 'policy.created', name: 'Policy Created', description: 'When a new policy is created' },
  { id: 'policy.deployed', name: 'Policy Deployed', description: 'When a policy is deployed' },
  { id: 'anomaly.detected', name: 'Anomaly Detected', description: 'When ML detects an anomaly' },
];

export const WebhookConfig: React.FC = () => {
  const [showCreateForm, setShowCreateForm] = useState(false);
  const queryClient = useQueryClient();

  const { data: webhooks } = useQuery({
    queryKey: ['webhooks'],
    queryFn: fetchWebhooks,
  });

  const deleteMutation = useMutation({
    mutationFn: deleteWebhook,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['webhooks'] }),
  });

  const toggleMutation = useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) =>
      updateWebhook(id, { enabled }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['webhooks'] }),
  });

  return (
    <div className="webhook-config">
      <div className="config-header">
        <h3>Webhooks</h3>
        <button onClick={() => setShowCreateForm(true)} className="btn-add">
          + Add Webhook
        </button>
      </div>

      {/* Webhook list */}
      <div className="webhook-list">
        {webhooks?.map((webhook) => (
          <div key={webhook.webhookId} className="webhook-card">
            <div className="webhook-info">
              <div className="webhook-url">
                <code>{webhook.url}</code>
                {webhook.failureCount > 0 && (
                  <span className="failure-badge">
                    {webhook.failureCount} failures
                  </span>
                )}
              </div>

              <div className="webhook-events">
                {webhook.events.map((event) => (
                  <span key={event} className="event-tag">{event}</span>
                ))}
              </div>

              {webhook.lastTriggered && (
                <span className="last-triggered">
                  Last triggered: {new Date(webhook.lastTriggered).toLocaleString()}
                </span>
              )}
            </div>

            <div className="webhook-actions">
              <label className="toggle">
                <input
                  type="checkbox"
                  checked={webhook.enabled}
                  onChange={(e) => toggleMutation.mutate({
                    id: webhook.webhookId,
                    enabled: e.target.checked,
                  })}
                />
                <span className="slider" />
              </label>

              <button
                className="btn-test"
                onClick={() => testWebhook(webhook.webhookId)}
              >
                Test
              </button>

              <button
                className="btn-delete"
                onClick={() => deleteMutation.mutate(webhook.webhookId)}
              >
                Delete
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Create form modal */}
      {showCreateForm && (
        <WebhookCreateForm
          eventTypes={EVENT_TYPES}
          onClose={() => setShowCreateForm(false)}
          onCreated={() => {
            setShowCreateForm(false);
            queryClient.invalidateQueries({ queryKey: ['webhooks'] });
          }}
        />
      )}
    </div>
  );
};

const WebhookCreateForm: React.FC<{
  eventTypes: typeof EVENT_TYPES;
  onClose: () => void;
  onCreated: () => void;
}> = ({ eventTypes, onClose, onCreated }) => {
  const [url, setUrl] = useState('');
  const [selectedEvents, setSelectedEvents] = useState<string[]>([]);

  const createMutation = useMutation({
    mutationFn: (data: { url: string; events: string[] }) => createWebhook(data),
    onSuccess: onCreated,
  });

  return (
    <div className="modal-overlay">
      <div className="modal-content webhook-form">
        <h3>Create Webhook</h3>

        <div className="form-field">
          <label>Endpoint URL</label>
          <input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://your-server.com/webhook"
          />
        </div>

        <div className="form-field">
          <label>Events to Subscribe</label>
          <div className="event-checkboxes">
            {eventTypes.map((event) => (
              <label key={event.id} className="event-checkbox">
                <input
                  type="checkbox"
                  checked={selectedEvents.includes(event.id)}
                  onChange={(e) => {
                    if (e.target.checked) {
                      setSelectedEvents([...selectedEvents, event.id]);
                    } else {
                      setSelectedEvents(selectedEvents.filter(e => e !== event.id));
                    }
                  }}
                />
                <div>
                  <span className="event-name">{event.name}</span>
                  <span className="event-desc">{event.description}</span>
                </div>
              </label>
            ))}
          </div>
        </div>

        <div className="form-actions">
          <button onClick={onClose} className="btn-cancel">Cancel</button>
          <button
            onClick={() => createMutation.mutate({ url, events: selectedEvents })}
            disabled={!url || selectedEvents.length === 0}
            className="btn-create"
          >
            Create Webhook
          </button>
        </div>
      </div>
    </div>
  );
};
```

### 4.2 Slack/Teams Setup Wizard

```tsx
// components/integrations/SlackSetupWizard.tsx
import React, { useState } from 'react';
import { useMutation } from '@tanstack/react-query';

export const SlackSetupWizard: React.FC<{ onComplete: () => void }> = ({ onComplete }) => {
  const [step, setStep] = useState(1);
  const [botToken, setBotToken] = useState('');
  const [defaultChannel, setDefaultChannel] = useState('');
  const [testResult, setTestResult] = useState<'pending' | 'success' | 'failed' | null>(null);

  const testMutation = useMutation({
    mutationFn: () => testSlackConnection(botToken, defaultChannel),
    onSuccess: () => setTestResult('success'),
    onError: () => setTestResult('failed'),
  });

  const saveMutation = useMutation({
    mutationFn: () => saveSlackIntegration(botToken, defaultChannel),
    onSuccess: onComplete,
  });

  return (
    <div className="slack-wizard">
      {step === 1 && (
        <div className="wizard-step">
          <h3>Step 1: Create a Slack App</h3>
          <ol>
            <li>Go to <a href="https://api.slack.com/apps" target="_blank">api.slack.com/apps</a></li>
            <li>Click "Create New App" → "From scratch"</li>
            <li>Name it "Sentinel Security" and select your workspace</li>
            <li>Under "OAuth & Permissions", add these scopes:
              <ul>
                <li><code>chat:write</code></li>
                <li><code>chat:write.public</code></li>
              </ul>
            </li>
            <li>Install the app to your workspace</li>
            <li>Copy the "Bot User OAuth Token"</li>
          </ol>
          <button onClick={() => setStep(2)} className="btn-next">
            I've created the app →
          </button>
        </div>
      )}

      {step === 2 && (
        <div className="wizard-step">
          <h3>Step 2: Configure Integration</h3>

          <div className="form-field">
            <label>Bot Token</label>
            <input
              type="password"
              value={botToken}
              onChange={(e) => setBotToken(e.target.value)}
              placeholder="xoxb-..."
            />
          </div>

          <div className="form-field">
            <label>Default Channel</label>
            <input
              type="text"
              value={defaultChannel}
              onChange={(e) => setDefaultChannel(e.target.value)}
              placeholder="#security-alerts"
            />
          </div>

          <div className="wizard-actions">
            <button onClick={() => setStep(1)} className="btn-back">
              ← Back
            </button>
            <button
              onClick={() => {
                setTestResult('pending');
                testMutation.mutate();
              }}
              className="btn-test"
              disabled={!botToken || !defaultChannel}
            >
              Test Connection
            </button>
          </div>

          {testResult && (
            <div className={`test-result ${testResult}`}>
              {testResult === 'pending' && 'Testing...'}
              {testResult === 'success' && '✅ Connection successful!'}
              {testResult === 'failed' && '❌ Connection failed. Check your token.'}
            </div>
          )}

          {testResult === 'success' && (
            <button onClick={() => saveMutation.mutate()} className="btn-save">
              Save Integration
            </button>
          )}
        </div>
      )}
    </div>
  );
};
```

---

## 5. Component Specifications

### Component Hierarchy

```
src/
├── components/
│   ├── dashboard/
│   │   ├── ThreatMap.tsx
│   │   ├── AnomalyVisualization.tsx
│   │   ├── BehaviorTimeline.tsx
│   │   ├── ThreatFeedStatus.tsx
│   │   └── RealTimeMetrics.tsx
│   ├── policies/
│   │   ├── VersionHistory.tsx
│   │   ├── VersionDiff.tsx
│   │   ├── ABTestWizard.tsx
│   │   ├── ABTestResults.tsx
│   │   ├── DSLEditor.tsx
│   │   ├── TemplateBrowser.tsx
│   │   └── PolicySimulator.tsx
│   ├── analytics/
│   │   ├── TrendChart.tsx
│   │   ├── RiskHeatmap.tsx
│   │   ├── PredictionDisplay.tsx
│   │   └── ReportBuilder.tsx
│   ├── integrations/
│   │   ├── WebhookConfig.tsx
│   │   ├── SlackSetupWizard.tsx
│   │   ├── TeamsSetupWizard.tsx
│   │   ├── SIEMConnectionManager.tsx
│   │   └── IntegrationHealthStatus.tsx
│   └── shared/
│       ├── charts/
│       ├── forms/
│       └── layout/
├── hooks/
│   ├── useWebSocket.ts
│   ├── useThreatData.ts
│   ├── usePolicyVersions.ts
│   └── useIntegrations.ts
├── services/
│   ├── api.ts
│   ├── websocket.ts
│   └── analytics.ts
└── store/
    ├── threatStore.ts
    ├── policyStore.ts
    └── integrationStore.ts
```

---

## 6. State Management

### React Query for Server State

```tsx
// hooks/useThreatData.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

export const useThreatData = (orgId: string, timeRange: string) => {
  return useQuery({
    queryKey: ['threats', orgId, timeRange],
    queryFn: () => fetchThreats(orgId, timeRange),
    staleTime: 30000, // 30 seconds
    refetchInterval: 30000,
  });
};

export const useAnomalyData = (orgId: string, userId?: string) => {
  return useQuery({
    queryKey: ['anomalies', orgId, userId],
    queryFn: () => fetchAnomalies(orgId, userId),
    enabled: !!orgId,
  });
};

export const usePolicyVersions = (policyId: string) => {
  return useQuery({
    queryKey: ['policyVersions', policyId],
    queryFn: () => fetchPolicyVersions(policyId),
  });
};

export const useCreatePolicyVersion = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createPolicyVersion,
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: ['policyVersions', variables.policyId]
      });
    },
  });
};
```

### Zustand for Client State

```tsx
// store/dashboardStore.ts
import { create } from 'zustand';

interface DashboardState {
  timeRange: '1h' | '24h' | '7d' | '30d';
  selectedThreat: string | null;
  liveUpdatesEnabled: boolean;
  setTimeRange: (range: '1h' | '24h' | '7d' | '30d') => void;
  setSelectedThreat: (id: string | null) => void;
  toggleLiveUpdates: () => void;
}

export const useDashboardStore = create<DashboardState>((set) => ({
  timeRange: '24h',
  selectedThreat: null,
  liveUpdatesEnabled: true,
  setTimeRange: (range) => set({ timeRange: range }),
  setSelectedThreat: (id) => set({ selectedThreat: id }),
  toggleLiveUpdates: () => set((state) => ({
    liveUpdatesEnabled: !state.liveUpdatesEnabled
  })),
}));
```

---

## 7. API Integration

### API Client

```tsx
// services/api.ts
import axios from 'axios';

const api = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for auth
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('authToken');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor for errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Handle unauthorized
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Threat endpoints
export const fetchThreats = (orgId: string, timeRange: string) =>
  api.get(`/threats?orgId=${orgId}&timeRange=${timeRange}`).then(r => r.data);

export const fetchAnomalies = (orgId: string, userId?: string) =>
  api.get(`/ml/anomalies?orgId=${orgId}${userId ? `&userId=${userId}` : ''}`).then(r => r.data);

// Policy endpoints
export const fetchPolicyVersions = (policyId: string) =>
  api.get(`/policies/${policyId}/versions`).then(r => r.data);

export const createPolicyVersion = (data: { policyId: string; changes: any; message: string }) =>
  api.post(`/policies/${data.policyId}/versions`, data).then(r => r.data);

export const rollbackPolicy = (policyId: string, targetVersion: number) =>
  api.post(`/policies/${policyId}/rollback`, { targetVersion }).then(r => r.data);

// A/B test endpoints
export const createABTest = (config: any) =>
  api.post('/ab-tests', config).then(r => r.data);

export const fetchABTestResults = (testId: string) =>
  api.get(`/ab-tests/${testId}/results`).then(r => r.data);

// Template endpoints
export const fetchTemplates = (category?: string) =>
  api.get(`/policies/templates${category ? `?category=${category}` : ''}`).then(r => r.data);

export const instantiateTemplate = (data: { templateId: string; name: string; variables: any }) =>
  api.post('/policies/templates/instantiate', data).then(r => r.data);

// Webhook endpoints
export const fetchWebhooks = () =>
  api.get('/webhooks').then(r => r.data);

export const createWebhook = (data: { url: string; events: string[] }) =>
  api.post('/webhooks', data).then(r => r.data);

export const deleteWebhook = (id: string) =>
  api.delete(`/webhooks/${id}`);

export const testWebhook = (id: string) =>
  api.post(`/webhooks/${id}/test`).then(r => r.data);

// Integration endpoints
export const testSlackConnection = (token: string, channel: string) =>
  api.post('/integrations/slack/test', { token, channel }).then(r => r.data);

export const saveSlackIntegration = (token: string, channel: string) =>
  api.post('/integrations/slack', { token, channel }).then(r => r.data);
```

### WebSocket Integration

```tsx
// services/websocket.ts
class WebSocketService {
  private ws: WebSocket | null = null;
  private listeners: Map<string, Set<(data: any) => void>> = new Map();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;

  connect(orgId: string) {
    const wsUrl = `${WS_BASE_URL}/ws/${orgId}`;
    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      console.log('WebSocket connected');
      this.reconnectAttempts = 0;
    };

    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      const { type, payload } = data;

      this.listeners.get(type)?.forEach(callback => callback(payload));
    };

    this.ws.onclose = () => {
      if (this.reconnectAttempts < this.maxReconnectAttempts) {
        setTimeout(() => {
          this.reconnectAttempts++;
          this.connect(orgId);
        }, 1000 * Math.pow(2, this.reconnectAttempts));
      }
    };
  }

  subscribe(eventType: string, callback: (data: any) => void) {
    if (!this.listeners.has(eventType)) {
      this.listeners.set(eventType, new Set());
    }
    this.listeners.get(eventType)!.add(callback);

    return () => {
      this.listeners.get(eventType)?.delete(callback);
    };
  }

  disconnect() {
    this.ws?.close();
    this.ws = null;
    this.listeners.clear();
  }
}

export const wsService = new WebSocketService();
```

---

## Summary

This frontend implementation guide covers:

1. **Advanced Threat Dashboard:** Real-time threat map, anomaly visualizations, behavior timeline
2. **Policy Management UI:** Version history, A/B test wizard, DSL editor with syntax highlighting, template browser
3. **Security Analytics:** Interactive trend charts, risk heatmaps
4. **Integration Management:** Webhook configuration, Slack/Teams setup wizards

Key technologies:
- React with TypeScript
- React Query for server state
- Zustand for client state
- Recharts for visualizations
- CodeMirror for DSL editor
- Framer Motion for animations

Estimated implementation time: 4-6 weeks with 1-2 frontend engineers.
