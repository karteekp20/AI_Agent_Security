import React, { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { apiClient } from '../../api/client';

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

const fetchTemplates = async (category: string | null): Promise<PolicyTemplate[]> => {
  const response = await apiClient.get<PolicyTemplate[]>('/policies/templates', {
    params: category ? { category } : {},
  });
  // Handle both array and object response formats
  return Array.isArray(response.data) ? response.data : response.data.templates || [];
};

const instantiateTemplate = async (data: {
  templateId: string;
  name: string;
  variables: Record<string, any>;
}): Promise<any> => {
  // Build request matching CreatePolicyRequest schema
  const request = {
    policy_name: data.name,
    policy_type: 'custom',
    pattern_value: '.*', // Placeholder for template-based policies
    action: 'warn',
    severity: 'medium',
    description: `Created from template: ${data.templateId}`,
    is_active: true,
    test_percentage: 0,
  };
  
  const response = await apiClient.post<any>(
    '/policies/templates/instantiate',
    request
  );
  return response.data;
};

export const TemplateBrowser: React.FC = () => {
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [selectedTemplate, setSelectedTemplate] = useState<PolicyTemplate | null>(null);
  const [variableValues, setVariableValues] = useState<Record<string, any>>({});

  const { data: templates } = useQuery({
    queryKey: ['policyTemplates', selectedCategory],
    queryFn: () => fetchTemplates(selectedCategory),
  });

  // Clear selected template when category changes
  React.useEffect(() => {
    setSelectedTemplate(null);
    setVariableValues({});
  }, [selectedCategory]);

  const instantiateMutation = useMutation({
    mutationFn: (data: { templateId: string; name: string; variables: Record<string, any> }) =>
      instantiateTemplate(data),
    onSuccess: (policy) => {
      // Reset form and show success
      setSelectedTemplate(null);
      setVariableValues({});
      alert(`Policy "${policy.policy_name}" created successfully!`);
    },
    onError: (error: any) => {
      const message = error.response?.data?.detail || error.message || 'Failed to create policy';
      alert(`Error: ${message}`);
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
          {templates?.map((template: PolicyTemplate) => (
            <div
              key={template.templateId}
              className={`template-card ${
                selectedTemplate?.templateId === template.templateId ? 'selected' : ''
              }`}
              onClick={() => {
                setSelectedTemplate(template);
                // Initialize variables with defaults
                const defaults: Record<string, any> = {};
                if (template.variables) {
                  Object.entries(template.variables).forEach(([key, spec]: [string, any]) => {
                    defaults[key] = spec.default;
                  });
                }
                setVariableValues(defaults);
              }}
            >
              <h4>{template.name}</h4>
              <p>{template.description}</p>

              <div className="template-meta">
                <span className="category-badge">{template.category}</span>
                {template.complianceFrameworks?.map((fw: string) => (
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
              {selectedTemplate.variables && Object.entries(selectedTemplate.variables).length > 0 ? (
                Object.entries(selectedTemplate.variables).map(([key, spec]: [string, any]) => (
                  <div key={key} className="variable-field">
                    <label>{key}</label>
                    {spec.description && <p className="help">{spec.description}</p>}

                    <VariableInput
                      spec={spec}
                      value={variableValues[key]}
                      onChange={(val) => setVariableValues({ ...variableValues, [key]: val })}
                    />
                  </div>
                ))
              ) : (
                <p className="no-variables">No additional configuration needed for this template</p>
              )}
            </div>

            <div className="config-actions">
              <input
                type="text"
                placeholder="Policy name"
                id="policy-name-input"
                className="policy-name-input"
              />
              <button
                className="btn-create"
                onClick={() => {
                  const nameInput = (document.getElementById('policy-name-input') as HTMLInputElement)?.value;
                  const policyName = nameInput?.trim() || 'New Policy from Template';
                  instantiateMutation.mutate({
                    templateId: selectedTemplate.templateId,
                    name: policyName,
                    variables: variableValues,
                  });
                }}
                disabled={instantiateMutation.isPending}
              >
                {instantiateMutation.isPending ? 'Creating...' : 'Create Policy'}
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