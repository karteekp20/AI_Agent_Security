import React, { useCallback, useMemo } from 'react';

interface DSLEditorProps {
  value: string;
  onChange: (value: string) => void;
  onValidate?: (errors: string[]) => void;
  readOnly?: boolean;
}

// Helper function for debouncing
const debounce = <T extends (...args: any[]) => any>(func: T, wait: number) => {
  let timeout: ReturnType<typeof setTimeout> | null = null;
  return (...args: Parameters<T>) => {
    if (timeout) clearTimeout(timeout);
    timeout = setTimeout(() => func(...args), wait);
  };
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

// Format code (simple implementation)
const formatCode = (code: string): string => {
  return code
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => line.length > 0)
    .join('\n');
};

// Insert snippet
const insertSnippet = (key: keyof typeof SNIPPETS): string => {
  return SNIPPETS[key] || '';
};

export const DSLEditor: React.FC<DSLEditorProps> = ({
  value,
  onChange,
  onValidate,
  readOnly = false,
}) => {
  // Validate DSL syntax
  const validateDSL = useCallback(async (code: string) => {
    try {
      const response = await fetch('http://localhost:8000/api/v1/policies/dsl/validate', {
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

  const handleChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const val = e.target.value;
    onChange(val);
    debouncedValidate(val);
  }, [onChange, debouncedValidate]);

  const handleInsertSnippet = useCallback((snippetKey: keyof typeof SNIPPETS) => {
    const snippet = insertSnippet(snippetKey);
    onChange(value ? `${value}\n\n${snippet}` : snippet);
  }, [onChange, value]);

  return (
    <div className="dsl-editor">
      <div className="editor-toolbar">
        <span className="editor-title">Policy DSL</span>
        <div className="toolbar-actions">
          <button 
            className="btn-format" 
            onClick={() => onChange(formatCode(value))}
          >
            Format
          </button>
          <button className="btn-docs" onClick={() => window.open('/docs/dsl')}>
            Documentation
          </button>
        </div>
      </div>

      <textarea
        value={value}
        onChange={handleChange}
        readOnly={readOnly}
        className="dsl-textarea"
        style={{
          width: '100%',
          height: '400px',
          fontFamily: 'monospace',
          fontSize: '14px',
          padding: '12px',
          backgroundColor: '#1e1e2e',
          color: '#cdd6f4',
          border: '1px solid #45475a',
          borderRadius: '4px',
          resize: 'vertical',
        }}
        placeholder="Enter your Sentinel DSL policy here..."
      />

      {/* Example snippets */}
      <div className="dsl-snippets">
        <h5>Quick Snippets</h5>
        <div className="snippet-buttons" style={{ display: 'flex', gap: '8px', marginTop: '8px' }}>
          <button 
            className="snippet-btn"
            onClick={() => handleInsertSnippet('pii-block')}
          >
            Block PII
          </button>
          <button 
            className="snippet-btn"
            onClick={() => handleInsertSnippet('injection-detect')}
          >
            Detect Injection
          </button>
          <button 
            className="snippet-btn"
            onClick={() => handleInsertSnippet('risk-threshold')}
          >
            Risk Threshold
          </button>
        </div>
      </div>
    </div>
  );
};
