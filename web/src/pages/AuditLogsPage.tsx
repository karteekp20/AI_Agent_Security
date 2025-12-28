import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuditLogs } from '@/hooks/useAudit';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Shield, Search, Filter, ChevronLeft, ChevronRight, AlertCircle, Loader2, Download } from 'lucide-react';
import { cn } from '@/lib/utils';
import { exportAuditLogsToCSV, exportAuditLogsToJSON } from '@/utils/export';
import type { AuditLog } from '@/api/audit';

export function AuditLogsPage() {
  const navigate = useNavigate();
  const [search, setSearch] = useState('');
  const [blockedOnly, setBlockedOnly] = useState(false);
  const [piiOnly, setPiiOnly] = useState(false);
  const [injectionOnly, setInjectionOnly] = useState(false);
  const [minRiskScore, setMinRiskScore] = useState<number | undefined>(undefined);
  const [page, setPage] = useState(1);
  const [selectedLog, setSelectedLog] = useState<AuditLog | null>(null);

  const pageSize = 10;

  const { data, isLoading, error } = useAuditLogs({
    search: search || undefined,
    blocked_only: blockedOnly,
    pii_only: piiOnly,
    injection_only: injectionOnly,
    min_risk_score: minRiskScore,
    page,
    page_size: pageSize,
  });

  const getRiskLevelColor = (riskScore?: number) => {
    if (!riskScore) return 'secondary';
    if (riskScore >= 0.7) return 'destructive';
    if (riskScore >= 0.4) return 'warning';
    return 'success';
  };

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString();
  };

  const totalPages = data ? Math.ceil(data.total / pageSize) : 0;

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4">
        <Card className="max-w-md">
          <CardHeader>
            <CardTitle className="flex items-center text-destructive">
              <AlertCircle className="h-5 w-5 mr-2" />
              Error Loading Audit Logs
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Failed to load audit logs. Please ensure the backend server is running.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950">
      <div className="container mx-auto px-4 py-8">
        <div className="space-y-6">
          {/* Title and Filters */}
          <div>
            <h2 className="text-3xl font-bold">Security Audit Logs</h2>
            <p className="text-muted-foreground mt-1">
              View and filter all security events and threat detections
            </p>
          </div>

          {/* Filters Card */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center text-lg">
                <Filter className="h-5 w-5 mr-2" />
                Filters
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Search */}
              <div>
                <Label>Search User Input</Label>
                <div className="relative mt-1">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    placeholder="Search in user input..."
                    className="pl-10"
                  />
                </div>
              </div>

              {/* Checkboxes */}
              <div className="grid grid-cols-3 gap-4">
                <label className="flex items-center space-x-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={blockedOnly}
                    onChange={(e) => setBlockedOnly(e.target.checked)}
                    className="w-4 h-4 rounded"
                  />
                  <span className="text-sm">Blocked Only</span>
                </label>
                <label className="flex items-center space-x-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={piiOnly}
                    onChange={(e) => setPiiOnly(e.target.checked)}
                    className="w-4 h-4 rounded"
                  />
                  <span className="text-sm">PII Only</span>
                </label>
                <label className="flex items-center space-x-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={injectionOnly}
                    onChange={(e) => setInjectionOnly(e.target.checked)}
                    className="w-4 h-4 rounded"
                  />
                  <span className="text-sm">Injection Only</span>
                </label>
              </div>

              {/* Risk Score Filter */}
              <div>
                <Label>Minimum Risk Score: {minRiskScore !== undefined ? minRiskScore.toFixed(2) : 'All'}</Label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.1"
                  value={minRiskScore ?? 0}
                  onChange={(e) => {
                    const value = parseFloat(e.target.value);
                    setMinRiskScore(value > 0 ? value : undefined);
                  }}
                  className="w-full mt-2"
                />
              </div>

              {/* Clear Filters */}
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setSearch('');
                  setBlockedOnly(false);
                  setPiiOnly(false);
                  setInjectionOnly(false);
                  setMinRiskScore(undefined);
                  setPage(1);
                }}
              >
                Clear Filters
              </Button>
            </CardContent>
          </Card>

          {/* Results Summary and Export */}
          <div className="flex items-center justify-between">
            <div className="text-sm text-muted-foreground">
              Showing {data?.logs.length || 0} of {data?.total || 0} logs
            </div>
            {data && data.logs.length > 0 && (
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => exportAuditLogsToCSV(data.logs)}
                >
                  <Download className="h-4 w-4 mr-2" />
                  Export CSV
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => exportAuditLogsToJSON(data.logs)}
                >
                  <Download className="h-4 w-4 mr-2" />
                  Export JSON
                </Button>
              </div>
            )}
          </div>

          {/* Audit Logs Table */}
          <Card>
            <CardContent className="p-0">
              {data?.logs.length === 0 ? (
                <div className="py-12 text-center">
                  <Shield className="h-12 w-12 mx-auto mb-4 text-muted-foreground opacity-50" />
                  <h3 className="text-lg font-semibold mb-2">No audit logs found</h3>
                  <p className="text-sm text-muted-foreground">
                    Try adjusting your filters or wait for security events to be logged.
                  </p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-slate-50 dark:bg-slate-900 border-b">
                      <tr>
                        <th className="px-4 py-3 text-left text-xs font-medium">Timestamp</th>
                        <th className="px-4 py-3 text-left text-xs font-medium">User Input</th>
                        <th className="px-4 py-3 text-left text-xs font-medium">Risk</th>
                        <th className="px-4 py-3 text-left text-xs font-medium">Status</th>
                        <th className="px-4 py-3 text-left text-xs font-medium">Threats</th>
                        <th className="px-4 py-3 text-left text-xs font-medium">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y">
                      {data?.logs.map((log) => (
                        <tr key={log.id} className="hover:bg-slate-50 dark:hover:bg-slate-900/50">
                          <td className="px-4 py-3 text-sm">
                            {formatTimestamp(log.timestamp)}
                          </td>
                          <td className="px-4 py-3 text-sm max-w-xs truncate">
                            {log.user_input}
                          </td>
                          <td className="px-4 py-3">
                            {log.risk_score !== undefined ? (
                              <Badge variant={getRiskLevelColor(log.risk_score)}>
                                {log.risk_score.toFixed(2)}
                              </Badge>
                            ) : (
                              <span className="text-xs text-muted-foreground">N/A</span>
                            )}
                          </td>
                          <td className="px-4 py-3">
                            {log.blocked ? (
                              <Badge variant="destructive">Blocked</Badge>
                            ) : (
                              <Badge variant="success">Allowed</Badge>
                            )}
                          </td>
                          <td className="px-4 py-3">
                            <div className="flex gap-1">
                              {log.pii_detected && (
                                <Badge variant="warning" className="text-xs">PII</Badge>
                              )}
                              {log.injection_detected && (
                                <Badge variant="destructive" className="text-xs">Injection</Badge>
                              )}
                              {log.escalated && (
                                <Badge variant="secondary" className="text-xs">Escalated</Badge>
                              )}
                            </div>
                          </td>
                          <td className="px-4 py-3">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => setSelectedLog(log)}
                            >
                              View Details
                            </Button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between">
              <p className="text-sm text-muted-foreground">
                Page {page} of {totalPages}
              </p>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                >
                  <ChevronLeft className="h-4 w-4" />
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                >
                  Next
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
            </div>
          )}

          {/* Detail Modal */}
          {selectedLog && (
            <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
              <Card className="max-w-2xl w-full max-h-[80vh] overflow-y-auto">
                <CardHeader>
                  <CardTitle>Audit Log Details</CardTitle>
                  <CardDescription>ID: {selectedLog.id}</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="text-muted-foreground">Timestamp:</span>
                      <p className="font-medium">{formatTimestamp(selectedLog.timestamp)}</p>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Session ID:</span>
                      <p className="font-mono text-xs">{selectedLog.session_id}</p>
                    </div>
                    {selectedLog.user_id && (
                      <div>
                        <span className="text-muted-foreground">User ID:</span>
                        <p className="font-medium">{selectedLog.user_id}</p>
                      </div>
                    )}
                    {selectedLog.ip_address && (
                      <div>
                        <span className="text-muted-foreground">IP Address:</span>
                        <p className="font-mono">{selectedLog.ip_address}</p>
                      </div>
                    )}
                  </div>

                  <div>
                    <span className="text-sm text-muted-foreground">User Input:</span>
                    <p className="mt-1 p-3 bg-secondary rounded text-sm">{selectedLog.user_input}</p>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <span className="text-sm text-muted-foreground">Risk Score:</span>
                      <p className="font-medium">
                        {selectedLog.risk_score !== undefined ? (
                          <Badge variant={getRiskLevelColor(selectedLog.risk_score)}>
                            {selectedLog.risk_score.toFixed(2)} - {selectedLog.risk_level}
                          </Badge>
                        ) : 'N/A'}
                      </p>
                    </div>
                    <div>
                      <span className="text-sm text-muted-foreground">Status:</span>
                      <p className="font-medium">
                        {selectedLog.blocked ? (
                          <Badge variant="destructive">Blocked</Badge>
                        ) : (
                          <Badge variant="success">Allowed</Badge>
                        )}
                      </p>
                    </div>
                  </div>

                  {selectedLog.pii_detected && (
                    <div>
                      <span className="text-sm text-muted-foreground">PII Detection:</span>
                      <p className="mt-1">
                        <Badge variant="warning">
                          {selectedLog.redacted_count} entities redacted
                        </Badge>
                      </p>
                      {selectedLog.pii_entities && (
                        <pre className="mt-2 p-2 bg-secondary rounded text-xs overflow-x-auto">
                          {JSON.stringify(selectedLog.pii_entities, null, 2)}
                        </pre>
                      )}
                    </div>
                  )}

                  {selectedLog.injection_detected && (
                    <div>
                      <span className="text-sm text-muted-foreground">Injection Detection:</span>
                      <p className="mt-1">
                        <Badge variant="destructive">
                          {selectedLog.injection_type || 'Detected'}
                          {selectedLog.injection_confidence && ` (${(selectedLog.injection_confidence * 100).toFixed(0)}%)`}
                        </Badge>
                      </p>
                    </div>
                  )}

                  <Button onClick={() => setSelectedLog(null)} className="w-full">
                    Close
                  </Button>
                </CardContent>
              </Card>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
