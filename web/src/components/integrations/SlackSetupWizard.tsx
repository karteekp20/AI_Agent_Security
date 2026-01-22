import React, { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { apiClient } from '../../api/client';

const testSlackConnection = async (botToken: string, defaultChannel: string): Promise<void> => {
  await apiClient.post('/integrations/slack/test', {
    bot_token: botToken,
    default_channel: defaultChannel,
  });
};

const saveSlackIntegration = async (botToken: string, defaultChannel: string): Promise<void> => {
  await apiClient.post('/integrations/slack', {
    bot_token: botToken,
    default_channel: defaultChannel,
  });
};

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