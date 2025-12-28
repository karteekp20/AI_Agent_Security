import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { usePolicies, useCreatePolicy, useDeletePolicy, useDeployPolicy, useTestPolicy } from '@/hooks/usePolicies';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Slider } from '@/components/ui/slider';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Shield, Plus, Trash2, Play, Pause, TestTube, Loader2, AlertCircle, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { Policy } from '@/api/types';

export function PoliciesPage() {
  const navigate = useNavigate();
  const [selectedPolicy, setSelectedPolicy] = useState<Policy | null>(null);
  const [testInput, setTestInput] = useState('');
  const [deployPercentage, setDeployPercentage] = useState(0);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [newPolicy, setNewPolicy] = useState({
    policy_name: '',
    policy_type: 'pii',
    pattern_value: '',
    action: 'block',
    severity: 'medium',
    description: '',
    is_active: true,
    test_percentage: 0,
  });

  const { data, isLoading, error } = usePolicies();
  const { mutate: createPolicy, isPending: isCreating } = useCreatePolicy();
  const { mutate: deletePolicy, isPending: isDeleting } = useDeletePolicy();
  const { mutate: deployPolicy, isPending: isDeploying } = useDeployPolicy();
  const { mutate: testPolicy, data: testResult, isPending: isTesting, reset: resetTest } = useTestPolicy();

  const handleCreatePolicy = () => {
    if (!newPolicy.policy_name.trim()) {
      alert('Please enter a policy name');
      return;
    }
    if (!newPolicy.pattern_value.trim()) {
      alert('Please enter a pattern');
      return;
    }

    createPolicy(newPolicy, {
      onSuccess: () => {
        setShowCreateDialog(false);
        setNewPolicy({
          policy_name: '',
          policy_type: 'pii',
          pattern_value: '',
          action: 'block',
          severity: 'medium',
          description: '',
          is_active: true,
          test_percentage: 0,
        });
      },
      onError: (error: any) => {
        alert(`Failed to create policy: ${error.response?.data?.detail || error.message}`);
      },
    });
  };

  const handleDelete = (policyId: string) => {
    if (confirm('Are you sure you want to delete this policy?')) {
      deletePolicy(policyId);
    }
  };

  const handleDeploy = (policyId: string, percentage: number) => {
    deployPolicy({
      policyId,
      data: { test_percentage: percentage },
    });
  };

  const handleTest = (policyId: string) => {
    if (!testInput.trim()) {
      alert('Please enter test input');
      return;
    }

    testPolicy({
      policyId,
      data: { test_input: testInput },
    });
  };

  const getPolicyTypeColor = (type: string) => {
    switch (type) {
      case 'pii':
        return 'warning';
      case 'injection':
        return 'destructive';
      case 'profanity':
        return 'secondary';
      default:
        return 'default';
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'destructive';
      case 'high':
        return 'destructive';
      case 'medium':
        return 'warning';
      case 'low':
        return 'secondary';
      default:
        return 'default';
    }
  };

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
              Error Loading Policies
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Failed to load policies. Please ensure the backend server is running.
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
          {/* Title and Create Button */}
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-3xl font-bold">Security Policies</h2>
              <p className="text-muted-foreground mt-1">
                Manage detection rules and response actions
              </p>
            </div>
            <Button onClick={() => setShowCreateDialog(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Create Policy
            </Button>
          </div>

          {/* Policies List */}
          <div className="grid gap-4">
            {data?.policies.length === 0 ? (
              <Card>
                <CardContent className="py-12 text-center">
                  <Shield className="h-12 w-12 mx-auto mb-4 text-muted-foreground opacity-50" />
                  <h3 className="text-lg font-semibold mb-2">No policies yet</h3>
                  <p className="text-sm text-muted-foreground mb-4">
                    Get started by creating your first security policy
                  </p>
                  <Button onClick={() => setShowCreateDialog(true)}>
                    <Plus className="h-4 w-4 mr-2" />
                    Create Policy
                  </Button>
                </CardContent>
              </Card>
            ) : (
              data?.policies.map((policy) => (
                <Card key={policy.policy_id} className="hover:shadow-md transition-shadow">
                  <CardHeader>
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center space-x-2 mb-2">
                          <CardTitle>{policy.policy_name}</CardTitle>
                          <Badge variant={getPolicyTypeColor(policy.policy_type)}>
                            {policy.policy_type}
                          </Badge>
                          <Badge variant={getSeverityColor(policy.severity)}>
                            {policy.severity}
                          </Badge>
                          {policy.is_active ? (
                            <Badge variant="success">Active</Badge>
                          ) : (
                            <Badge variant="secondary">Inactive</Badge>
                          )}
                        </div>
                        <CardDescription>
                          {policy.description || 'No description'}
                        </CardDescription>
                      </div>
                      <div className="flex items-center space-x-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            setSelectedPolicy(policy);
                            setTestInput('');
                            resetTest();
                          }}
                        >
                          <TestTube className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDelete(policy.policy_id)}
                          disabled={isDeleting}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      {/* Policy Details */}
                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                          <span className="text-muted-foreground">Pattern:</span>
                          <p className="font-mono text-xs mt-1 bg-secondary px-2 py-1 rounded">
                            {policy.pattern_value}
                          </p>
                        </div>
                        <div>
                          <span className="text-muted-foreground">Action:</span>
                          <p className="font-medium mt-1 capitalize">{policy.action}</p>
                        </div>
                        <div>
                          <span className="text-muted-foreground">Triggered:</span>
                          <p className="font-medium mt-1">{policy.triggered_count} times</p>
                        </div>
                        <div>
                          <span className="text-muted-foreground">False Positives:</span>
                          <p className="font-medium mt-1">{policy.false_positive_count}</p>
                        </div>
                      </div>

                      {/* Deployment Controls */}
                      <div className="pt-4 border-t">
                        <Label className="text-sm font-medium mb-2 block">
                          Canary Deployment: {policy.test_percentage}%
                        </Label>
                        <div className="flex items-center space-x-4">
                          <Slider
                            value={policy.test_percentage}
                            onValueChange={(value) => setDeployPercentage(value)}
                            min={0}
                            max={100}
                            step={10}
                            className="flex-1"
                          />
                          <Button
                            size="sm"
                            onClick={() => handleDeploy(policy.policy_id, deployPercentage)}
                            disabled={isDeploying}
                          >
                            {isDeploying ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : policy.is_active ? (
                              <>
                                <Pause className="h-4 w-4 mr-1" />
                                Update
                              </>
                            ) : (
                              <>
                                <Play className="h-4 w-4 mr-1" />
                                Deploy
                              </>
                            )}
                          </Button>
                        </div>
                        <p className="text-xs text-muted-foreground mt-2">
                          0% = Disabled | 1-99% = Canary | 100% = Fully Deployed
                        </p>
                      </div>

                      {/* Test Section (Expanded) */}
                      {selectedPolicy?.policy_id === policy.policy_id && (
                        <div className="pt-4 border-t space-y-4">
                          <div>
                            <Label>Test Input</Label>
                            <Input
                              value={testInput}
                              onChange={(e) => setTestInput(e.target.value)}
                              placeholder="Enter sample text to test this policy..."
                              className="mt-1"
                            />
                          </div>
                          <Button
                            onClick={() => handleTest(policy.policy_id)}
                            disabled={isTesting}
                            className="w-full"
                          >
                            {isTesting ? (
                              <>
                                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                Testing...
                              </>
                            ) : (
                              <>
                                <TestTube className="h-4 w-4 mr-2" />
                                Test Policy
                              </>
                            )}
                          </Button>

                          {/* Test Result */}
                          {testResult && (
                            <div
                              className={cn(
                                "p-4 rounded-lg border",
                                testResult.matched
                                  ? "bg-destructive/10 border-destructive/20"
                                  : "bg-green-500/10 border-green-500/20"
                              )}
                            >
                              <div className="flex items-start space-x-2">
                                <div
                                  className={cn(
                                    "mt-0.5",
                                    testResult.matched ? "text-destructive" : "text-green-600"
                                  )}
                                >
                                  <AlertCircle className="h-5 w-5" />
                                </div>
                                <div className="flex-1">
                                  <p className="font-medium">
                                    {testResult.matched ? 'Pattern Matched!' : 'No Match'}
                                  </p>
                                  <p className="text-sm text-muted-foreground mt-1">
                                    {testResult.explanation}
                                  </p>
                                  {testResult.matched && testResult.action_taken === 'redact' && testResult.redacted_output && (
                                    <div className="mt-2">
                                      <span className="text-sm font-medium">Redacted Output:</span>
                                      <p className="text-sm mt-1 bg-background px-2 py-1 rounded">
                                        {testResult.redacted_output}
                                      </p>
                                    </div>
                                  )}
                                </div>
                              </div>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </CardContent>
                </Card>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Create Policy Dialog */}
      {showCreateDialog && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
          <Card className="w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Create New Policy</CardTitle>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowCreateDialog(false)}
                  disabled={isCreating}
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
              <CardDescription>
                Define a new security policy with custom detection patterns
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="policy_name">Policy Name *</Label>
                <Input
                  id="policy_name"
                  placeholder="e.g., Credit Card Detection"
                  value={newPolicy.policy_name}
                  onChange={(e) => setNewPolicy({ ...newPolicy, policy_name: e.target.value })}
                  disabled={isCreating}
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="policy_type">Type *</Label>
                  <select
                    id="policy_type"
                    className="w-full h-10 px-3 rounded-md border border-input bg-background"
                    value={newPolicy.policy_type}
                    onChange={(e) => setNewPolicy({ ...newPolicy, policy_type: e.target.value })}
                    disabled={isCreating}
                  >
                    <option value="pii">PII Detection</option>
                    <option value="injection">Injection Detection</option>
                    <option value="profanity">Profanity Filter</option>
                    <option value="custom">Custom Pattern</option>
                  </select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="action">Action *</Label>
                  <select
                    id="action"
                    className="w-full h-10 px-3 rounded-md border border-input bg-background"
                    value={newPolicy.action}
                    onChange={(e) => setNewPolicy({ ...newPolicy, action: e.target.value })}
                    disabled={isCreating}
                  >
                    <option value="block">Block</option>
                    <option value="redact">Redact</option>
                    <option value="warn">Warn Only</option>
                    <option value="log">Log Only</option>
                  </select>
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="severity">Severity *</Label>
                <select
                  id="severity"
                  className="w-full h-10 px-3 rounded-md border border-input bg-background"
                  value={newPolicy.severity}
                  onChange={(e) => setNewPolicy({ ...newPolicy, severity: e.target.value })}
                  disabled={isCreating}
                >
                  <option value="critical">Critical</option>
                  <option value="high">High</option>
                  <option value="medium">Medium</option>
                  <option value="low">Low</option>
                </select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="pattern_value">Detection Pattern (Regex) *</Label>
                <Input
                  id="pattern_value"
                  placeholder="e.g., \d{4}-\d{4}-\d{4}-\d{4}"
                  value={newPolicy.pattern_value}
                  onChange={(e) => setNewPolicy({ ...newPolicy, pattern_value: e.target.value })}
                  disabled={isCreating}
                  className="font-mono"
                />
                <p className="text-xs text-muted-foreground">
                  Enter a regex pattern to detect. Example: <code className="px-1 py-0.5 bg-slate-100 dark:bg-slate-800 rounded">\d{"{16}"}</code> for 16-digit numbers
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="description">Description</Label>
                <textarea
                  id="description"
                  className="w-full min-h-[80px] px-3 py-2 rounded-md border border-input bg-background"
                  placeholder="Describe what this policy detects and why..."
                  value={newPolicy.description}
                  onChange={(e) => setNewPolicy({ ...newPolicy, description: e.target.value })}
                  disabled={isCreating}
                />
              </div>

              <div className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  id="is_active"
                  checked={newPolicy.is_active}
                  onChange={(e) => setNewPolicy({ ...newPolicy, is_active: e.target.checked })}
                  disabled={isCreating}
                  className="h-4 w-4 rounded border-gray-300"
                />
                <Label htmlFor="is_active" className="font-normal">
                  Activate policy immediately
                </Label>
              </div>

              <div className="flex justify-end space-x-2 pt-4">
                <Button
                  variant="outline"
                  onClick={() => setShowCreateDialog(false)}
                  disabled={isCreating}
                >
                  Cancel
                </Button>
                <Button onClick={handleCreatePolicy} disabled={isCreating}>
                  {isCreating ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Creating...
                    </>
                  ) : (
                    <>
                      <Plus className="h-4 w-4 mr-2" />
                      Create Policy
                    </>
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
