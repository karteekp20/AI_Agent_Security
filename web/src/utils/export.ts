/**
 * Export Utilities
 * Functions for exporting data to CSV, JSON, etc.
 */

import type { AuditLog } from '@/api/audit';

/**
 * Convert array of objects to CSV string
 */
export function convertToCSV<T extends Record<string, any>>(
  data: T[],
  headers?: Record<keyof T, string>
): string {
  if (data.length === 0) return '';

  // Get keys from first object
  const keys = Object.keys(data[0]) as (keyof T)[];

  // Create header row
  const headerRow = headers
    ? keys.map((key) => headers[key] || String(key)).join(',')
    : keys.join(',');

  // Create data rows
  const dataRows = data.map((item) => {
    return keys
      .map((key) => {
        const value = item[key];
        // Handle null/undefined
        if (value === null || value === undefined) return '';
        // Handle objects/arrays
        if (typeof value === 'object') return `"${JSON.stringify(value).replace(/"/g, '""')}"`;
        // Handle strings with commas or quotes
        if (typeof value === 'string' && (value.includes(',') || value.includes('"'))) {
          return `"${value.replace(/"/g, '""')}"`;
        }
        return String(value);
      })
      .join(',');
  });

  return [headerRow, ...dataRows].join('\n');
}

/**
 * Download CSV file
 */
export function downloadCSV(csvContent: string, filename: string) {
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');
  const url = URL.createObjectURL(blob);

  link.setAttribute('href', url);
  link.setAttribute('download', filename);
  link.style.visibility = 'hidden';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

/**
 * Download JSON file
 */
export function downloadJSON(data: any, filename: string) {
  const jsonContent = JSON.stringify(data, null, 2);
  const blob = new Blob([jsonContent], { type: 'application/json;charset=utf-8;' });
  const link = document.createElement('a');
  const url = URL.createObjectURL(blob);

  link.setAttribute('href', url);
  link.setAttribute('download', filename);
  link.style.visibility = 'hidden';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

/**
 * Export audit logs to CSV
 */
export function exportAuditLogsToCSV(logs: AuditLog[]) {
  const headers: Record<keyof AuditLog, string> = {
    id: 'ID',
    timestamp: 'Timestamp',
    session_id: 'Session ID',
    request_id: 'Request ID',
    org_id: 'Organization ID',
    workspace_id: 'Workspace ID',
    user_id: 'User ID',
    user_role: 'User Role',
    ip_address: 'IP Address',
    user_input: 'User Input',
    input_length: 'Input Length',
    blocked: 'Blocked',
    risk_score: 'Risk Score',
    risk_level: 'Risk Level',
    pii_detected: 'PII Detected',
    pii_entities: 'PII Entities',
    redacted_count: 'Redacted Count',
    injection_detected: 'Injection Detected',
    injection_type: 'Injection Type',
    injection_confidence: 'Injection Confidence',
    escalated: 'Escalated',
    escalated_to: 'Escalated To',
    metadata: 'Metadata',
  };

  const csvContent = convertToCSV(logs, headers);
  const filename = `audit-logs-${new Date().toISOString().split('T')[0]}.csv`;
  downloadCSV(csvContent, filename);
}

/**
 * Export audit logs to JSON
 */
export function exportAuditLogsToJSON(logs: AuditLog[]) {
  const filename = `audit-logs-${new Date().toISOString().split('T')[0]}.json`;
  downloadJSON(logs, filename);
}
