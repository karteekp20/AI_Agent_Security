import React, { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { apiClient } from '../../api/client';

interface Policy {
  policyId: string;
  name: string;
  status: string;
}

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

const fetchDraftPolicies = async (): Promise<Policy[]> => {
  try {
    const response = await apiClient.get('/policies', {
      params: { is_active: false },
    });
    // Handle both array and object response formats
    if (Array.isArray(response.data)) {
      return response.data;
    }
    return response.data.policies || [];
  } catch (error) {
    console.error('Error fetching policies:', error);
    return [];
  }
};

const createABTest = async (config: ABTestConfig): Promise<{ testId: string }> => {
  const response = await apiClient.post<{ testId: string }>(
    '/ab-tests',
    config
  );
  return response.data;
};

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
  const { data: policies = [] } = useQuery({
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
      {Array.isArray(policies) && policies.length > 0 ? (
        policies.map((policy: any) => (
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
        ))
        ) : (
        <div className="no-policies">
          <p>No inactive policies available for testing</p>
        </div>
        )}
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