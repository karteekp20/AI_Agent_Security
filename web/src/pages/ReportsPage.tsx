import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useReports, useGenerateReport, useDeleteReport, useDownloadReport } from '@/hooks/useReports';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { FileText, Plus, Download, Trash2, Loader2, AlertCircle, CheckCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { Report } from '@/api/reports';
import { TrendChart } from '@/components/analytics/TrendChart';

export function ReportsPage() {
  const navigate = useNavigate();
  const [showGenerateForm, setShowGenerateForm] = useState(false);
  const [reportName, setReportName] = useState('');
  const [reportType, setReportType] = useState<'pci_dss' | 'gdpr' | 'hipaa' | 'soc2'>('pci_dss');
  const [fileFormat, setFileFormat] = useState<'pdf' | 'excel' | 'json'>('pdf');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  const { data: reportsData, isLoading } = useReports();
  const { mutate: generateReport, isPending: isGenerating } = useGenerateReport();
  const { mutate: deleteReport, isPending: isDeleting } = useDeleteReport();
  const { mutate: downloadReport, isPending: isDownloading } = useDownloadReport();

  const handleGenerate = (e?: React.FormEvent) => {
    e?.preventDefault(); // Prevent page refresh on Enter

    if (!reportName || !startDate || !endDate) {
      alert('Please fill in all required fields');
      return;
    }

    generateReport(
      {
        report_name: reportName,
        report_type: reportType,
        file_format: fileFormat,
        date_range_start: new Date(startDate).toISOString(),
        date_range_end: new Date(endDate).toISOString(),
      },
      {
        onSuccess: () => {
          setShowGenerateForm(false);
          setReportName('');
          setStartDate('');
          setEndDate('');
        },
        onError: (error: any) => {
          alert(`Failed to generate report: ${error.response?.data?.detail || error.message}`);
        },
      }
    );
  };

  const handleDownload = (report: Report) => {
    const extension = report.file_format;
    const filename = `${report.report_name}.${extension}`;
    downloadReport({ reportId: report.report_id, filename });
  };

  const handleDelete = (reportId: string, reportName: string) => {
    if (confirm(`Are you sure you want to delete "${reportName}"?`)) {
      deleteReport(reportId);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return <Badge variant="success"><CheckCircle className="h-3 w-3 mr-1" />Completed</Badge>;
      case 'processing':
        return <Badge variant="secondary"><Loader2 className="h-3 w-3 mr-1 animate-spin" />Processing</Badge>;
      case 'pending':
        return <Badge variant="secondary">Pending</Badge>;
      case 'failed':
        return <Badge variant="destructive"><AlertCircle className="h-3 w-3 mr-1" />Failed</Badge>;
      default:
        return <Badge>{status}</Badge>;
    }
  };

  const getReportTypeName = (type: string) => {
    const names: Record<string, string> = {
      pci_dss: 'PCI-DSS',
      gdpr: 'GDPR',
      hipaa: 'HIPAA',
      soc2: 'SOC 2',
    };
    return names[type] || type;
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950">
      <div className="container mx-auto px-4 py-8">
        <div className="space-y-6">
          {/* Title and Generate Button */}
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-3xl font-bold">Compliance Reports</h2>
              <p className="text-muted-foreground mt-1">
                Generate and download compliance reports for PCI-DSS, GDPR, HIPAA, and SOC 2
              </p>
            </div>
            <Button onClick={() => setShowGenerateForm(!showGenerateForm)}>
              <Plus className="h-4 w-4 mr-2" />
              Generate Report
            </Button>
          </div>

          {/* Generate Report Form */}
          {showGenerateForm && (
            <Card>
              <CardHeader>
                <CardTitle>Generate New Report</CardTitle>
                <CardDescription>Create a compliance report for a specific time period</CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleGenerate} className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label>Report Name *</Label>
                    <Input
                      value={reportName}
                      onChange={(e) => setReportName(e.target.value)}
                      placeholder="Q4 2024 Compliance Report"
                      className="mt-1"
                    />
                  </div>
                  <div>
                    <Label>Report Type *</Label>
                    <select
                      value={reportType}
                      onChange={(e) => setReportType(e.target.value as any)}
                      className="w-full mt-1 px-3 py-2 border rounded-md"
                    >
                      <option value="pci_dss">PCI-DSS (Credit Card Data)</option>
                      <option value="gdpr">GDPR (Personal Data)</option>
                      <option value="hipaa">HIPAA (Health Information)</option>
                      <option value="soc2">SOC 2 (Trust Service Criteria)</option>
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <Label>Start Date *</Label>
                    <Input
                      type="date"
                      value={startDate}
                      onChange={(e) => setStartDate(e.target.value)}
                      className="mt-1"
                    />
                  </div>
                  <div>
                    <Label>End Date *</Label>
                    <Input
                      type="date"
                      value={endDate}
                      onChange={(e) => setEndDate(e.target.value)}
                      className="mt-1"
                    />
                  </div>
                  <div>
                    <Label>File Format</Label>
                    <select
                      value={fileFormat}
                      onChange={(e) => setFileFormat(e.target.value as any)}
                      className="w-full mt-1 px-3 py-2 border rounded-md"
                    >
                      <option value="pdf">PDF</option>
                      <option value="excel">Excel</option>
                      <option value="json">JSON</option>
                    </select>
                  </div>
                </div>

                <div className="flex gap-2">
                  <Button type="submit" disabled={isGenerating}>
                    {isGenerating ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Generating...
                      </>
                    ) : (
                      <>
                        <FileText className="h-4 w-4 mr-2" />
                        Generate Report
                      </>
                    )}
                  </Button>
                  <Button type="button" variant="outline" onClick={() => setShowGenerateForm(false)}>
                    Cancel
                  </Button>
                </div>
                </form>
              </CardContent>
            </Card>
          )}

          {/* Threat Trend Analytics */}
          <Card>
            <CardHeader>
              <CardTitle>Threat Trends</CardTitle>
              <CardDescription>Historical threat detection patterns</CardDescription>
            </CardHeader>
            <CardContent>
              <TrendChart
                data={[
                  { timestamp: new Date(Date.now() - 6 * 24 * 60 * 60 * 1000).toISOString(), value: 24, trend: 'stable' },
                  { timestamp: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000).toISOString(), value: 19, trend: 'down' },
                  { timestamp: new Date(Date.now() - 4 * 24 * 60 * 60 * 1000).toISOString(), value: 15, trend: 'down' },
                  { timestamp: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(), value: 18, trend: 'up' },
                  { timestamp: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(), value: 22, trend: 'up' },
                  { timestamp: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000).toISOString(), value: 28, trend: 'up' },
                  { timestamp: new Date().toISOString(), value: 32, trend: 'up' },
                ]}
                metric="Threats per Day"
                showAnomaly={false}
                showTrend={true}
              />
            </CardContent>
          </Card>

          {/* Reports List */}
          <Card>
            <CardHeader>
              <CardTitle>Generated Reports</CardTitle>
              <CardDescription>
                {reportsData?.total || 0} reports total
              </CardDescription>
            </CardHeader>
            <CardContent>
              {reportsData?.reports.length === 0 ? (
                <div className="text-center py-12">
                  <FileText className="h-12 w-12 mx-auto mb-4 text-muted-foreground opacity-50" />
                  <h3 className="text-lg font-semibold mb-2">No reports yet</h3>
                  <p className="text-sm text-muted-foreground mb-4">
                    Generate your first compliance report to get started
                  </p>
                  <Button onClick={() => setShowGenerateForm(true)}>
                    <Plus className="h-4 w-4 mr-2" />
                    Generate Report
                  </Button>
                </div>
              ) : (
                <div className="space-y-3">
                  {reportsData?.reports.map((report) => (
                    <div key={report.report_id} className="flex items-center justify-between p-4 border rounded-lg">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <h3 className="font-medium">{report.report_name}</h3>
                          <Badge variant="outline">{getReportTypeName(report.report_type)}</Badge>
                          {getStatusBadge(report.status)}
                        </div>
                        <div className="text-sm text-muted-foreground">
                          <span>Created: {new Date(report.created_at).toLocaleDateString()}</span>
                          {report.completed_at && (
                            <span className="ml-4">
                              Completed: {new Date(report.completed_at).toLocaleDateString()}
                            </span>
                          )}
                        </div>
                        {report.status === 'processing' && (
                          <div className="mt-2">
                            <div className="w-full bg-secondary rounded-full h-2">
                              <div
                                className="bg-primary rounded-full h-2 transition-all"
                                style={{ width: `${report.progress_percentage}%` }}
                              />
                            </div>
                            <span className="text-xs text-muted-foreground">
                              {report.progress_percentage}% complete
                            </span>
                          </div>
                        )}
                        {report.error_message && (
                          <p className="text-sm text-destructive mt-1">{report.error_message}</p>
                        )}
                      </div>
                      <div className="flex items-center gap-2 ml-4">
                        {report.status === 'completed' && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleDownload(report)}
                            disabled={isDownloading}
                          >
                            <Download className="h-4 w-4 mr-1" />
                            Download
                          </Button>
                        )}
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDelete(report.report_id, report.report_name)}
                          disabled={isDeleting}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
