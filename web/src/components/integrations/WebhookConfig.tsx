import React, { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../api/client';

interface Webhook {
  webhookId: string;
  url: string;
  events: string[];
  enabled: boolean;
  failureCount: number;
  lastTriggered?: string;
}

const fetchWebhooks = async (): Promise<Webhook[]> => {
  const response = await apiClient.get<Webhook[]>('/webhooks');
  return response.data;
};

const createWebhook = async (data: { url: string; events: string[] }): Promise<Webhook> => {
  const response = await apiClient.post<Webhook>('/webhooks', data);
  return response.data;
};

const deleteWebhook = async (webhookId: string): Promise<void> => {
  await apiClient.delete(`/api/v1/webhooks/${webhookId}`);
};

const updateWebhook = async (webhookId: string, data: { enabled?: boolean }): Promise<Webhook> => {
  const response = await apiClient.patch<Webhook>(`/api/v1/webhooks/${webhookId}`, data);
  return response.data;
};

const testWebhook = async (webhookId: string): Promise<void> => {
  await apiClient.post(`/api/v1/webhooks/${webhookId}/test`);
};

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
        {webhooks?.map((webhook: Webhook) => (
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
                 {webhook.events.map((event: string) => (
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