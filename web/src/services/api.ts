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