import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useOrganization, useOrganizationUsers, useInviteUser, useRemoveUser } from '@/hooks/useOrganizations';
import { useAPIKeys, useCreateAPIKey, useRevokeAPIKey } from '@/hooks/useAPIKeys';
import { useCurrentUser } from '@/hooks/useAuth';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Shield, Users, Key, Plus, Trash2, Loader2, AlertCircle, Copy, Check, Zap, MessageSquare } from 'lucide-react';
import { cn } from '@/lib/utils';
import { WebhookConfig } from '@/components/integrations/WebhookConfig';
import { SlackSetupWizard } from '@/components/integrations/SlackSetupWizard';

export function SettingsPage() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<'organization' | 'users' | 'api-keys' | 'security' | 'integrations'>('organization');
  const [showSlackSetup, setShowSlackSetup] = useState(false);
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteFullName, setInviteFullName] = useState('');
  const [inviteRole, setInviteRole] = useState('member');
  const [newKeyName, setNewKeyName] = useState('');
  const [createdKey, setCreatedKey] = useState<string | null>(null);
  const [copiedKey, setCopiedKey] = useState(false);
  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const [tempPasswordData, setTempPasswordData] = useState<{ email: string; password: string } | null>(null);
  const [passwordCopied, setPasswordCopied] = useState(false);

  const { data: currentUser } = useCurrentUser();
  const isAdminOrOwner = currentUser?.role === 'admin' || currentUser?.role === 'owner';

  const { data: orgData, isLoading: orgLoading } = useOrganization();
  const { data: usersData, isLoading: usersLoading } = useOrganizationUsers();
  const { data: keysData, isLoading: keysLoading } = useAPIKeys();

  const { mutate: inviteUser, isPending: isInviting } = useInviteUser();
  const { mutate: removeUser, isPending: isRemoving } = useRemoveUser();
  const { mutate: createAPIKey, isPending: isCreatingKey } = useCreateAPIKey();
  const { mutate: revokeAPIKey, isPending: isRevokingKey } = useRevokeAPIKey();

  const handleInviteUser = () => {
    if (!inviteFullName.trim()) {
      alert('Please enter the user\'s full name');
      return;
    }

    if (!inviteEmail.trim()) {
      alert('Please enter an email address');
      return;
    }

    inviteUser(
      { email: inviteEmail, full_name: inviteFullName, role: inviteRole },
      {
        onSuccess: (data) => {
          setTempPasswordData({
            email: inviteEmail,
            password: data.temporary_password
          });
          setShowPasswordModal(true);
          setInviteEmail('');
          setInviteFullName('');
        },
        onError: (error: any) => {
          alert(`Failed to invite user: ${error.response?.data?.detail || error.message}`);
        },
      }
    );
  };

  const handleCopyPassword = () => {
    if (tempPasswordData) {
      navigator.clipboard.writeText(tempPasswordData.password);
      setPasswordCopied(true);
      setTimeout(() => setPasswordCopied(false), 2000);
    }
  };

  const handleCloseModal = () => {
    setShowPasswordModal(false);
    setTempPasswordData(null);
    setPasswordCopied(false);
  };

  const handleRemoveUser = (userId: string, email: string) => {
    if (confirm(`Are you sure you want to remove ${email}?`)) {
      removeUser(userId, {
        onError: (error: any) => {
          alert(`Failed to remove user: ${error.response?.data?.detail || error.message}`);
        },
      });
    }
  };

  const handleCreateAPIKey = () => {
    if (!newKeyName.trim()) {
      alert('Please enter a key name');
      return;
    }

    createAPIKey(
      { key_name: newKeyName },
      {
        onSuccess: (data) => {
          setCreatedKey(data.api_key);
          setNewKeyName('');
        },
        onError: (error: any) => {
          alert(`Failed to create API key: ${error.response?.data?.detail || error.message}`);
        },
      }
    );
  };

  const handleRevokeAPIKey = (keyId: string, keyName: string) => {
    if (confirm(`Are you sure you want to revoke "${keyName || 'this API key'}"?`)) {
      revokeAPIKey(keyId, {
        onError: (error: any) => {
          alert(`Failed to revoke API key: ${error.response?.data?.detail || error.message}`);
        },
      });
    }
  };

  const handleCopyKey = () => {
    if (createdKey) {
      navigator.clipboard.writeText(createdKey);
      setCopiedKey(true);
      setTimeout(() => setCopiedKey(false), 2000);
    }
  };

  const getRoleBadgeVariant = (role: string) => {
    switch (role) {
      case 'owner':
        return 'destructive';
      case 'admin':
        return 'warning';
      case 'member':
        return 'default';
      case 'viewer':
        return 'secondary';
      default:
        return 'outline';
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950">
      <div className="container mx-auto px-4 py-8">
        <div className="space-y-6">
          {/* Title */}
          <div>
            <h2 className="text-3xl font-bold">Settings</h2>
            <p className="text-muted-foreground mt-1">
              Manage your organization, users, and API keys
            </p>
          </div>

          {/* Tabs */}
          <div className="flex gap-2 border-b">
            <button
              onClick={() => setActiveTab('organization')}
              className={cn(
                'px-4 py-2 font-medium border-b-2 transition-colors',
                activeTab === 'organization'
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground'
              )}
            >
              Organization
            </button>
            <button
              onClick={() => setActiveTab('users')}
              className={cn(
                'px-4 py-2 font-medium border-b-2 transition-colors',
                activeTab === 'users'
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground'
              )}
            >
              <Users className="h-4 w-4 inline mr-2" />
              Users
            </button>
            <button
              onClick={() => setActiveTab('api-keys')}
              className={cn(
                'px-4 py-2 font-medium border-b-2 transition-colors',
                activeTab === 'api-keys'
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground'
              )}
            >
              <Key className="h-4 w-4 inline mr-2" />
              API Keys
            </button>
            <button
              onClick={() => setActiveTab('security')}
              className={cn(
                'px-4 py-2 font-medium border-b-2 transition-colors',
                activeTab === 'security'
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground'
              )}
            >
              <Shield className="h-4 w-4 inline mr-2" />
              Security
            </button>
            <button
              onClick={() => setActiveTab('integrations')}
              className={cn(
                'px-4 py-2 font-medium border-b-2 transition-colors',
                activeTab === 'integrations'
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground'
              )}
            >
              <Zap className="h-4 w-4 inline mr-2" />
              Integrations
            </button>
          </div>

          {/* Organization Tab */}
          {activeTab === 'organization' && (
            <div className="space-y-4">
              {orgLoading ? (
                <div className="flex justify-center py-8">
                  <Loader2 className="h-8 w-8 animate-spin text-primary" />
                </div>
              ) : (
                <Card>
                  <CardHeader>
                    <CardTitle>Organization Information</CardTitle>
                    <CardDescription>View your organization details and usage</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <Label>Organization Name</Label>
                        <p className="text-lg font-medium mt-1">{orgData?.org_name}</p>
                      </div>
                      <div>
                        <Label>Organization ID</Label>
                        <p className="text-sm font-mono mt-1">{orgData?.org_id}</p>
                      </div>
                      <div>
                        <Label>Plan</Label>
                        <p className="mt-1">
                          <Badge variant="success">{orgData?.plan || 'Free'}</Badge>
                        </p>
                      </div>
                      <div>
                        <Label>Status</Label>
                        <p className="mt-1">
                          {orgData?.is_active ? (
                            <Badge variant="success">Active</Badge>
                          ) : (
                            <Badge variant="destructive">Suspended</Badge>
                          )}
                        </p>
                      </div>
                    </div>

                    <div className="pt-4 border-t">
                      <Label>API Usage This Month</Label>
                      <div className="mt-2 space-y-2">
                        <div className="flex justify-between text-sm">
                          <span>Requests</span>
                          <span className="font-medium">
                            {orgData?.api_requests_this_month?.toLocaleString() || 0} / {orgData?.max_api_requests_per_month?.toLocaleString() || 'Unlimited'}
                          </span>
                        </div>
                        <div className="w-full bg-secondary rounded-full h-2">
                          <div
                            className="bg-primary rounded-full h-2 transition-all"
                            style={{
                              width: orgData?.max_api_requests_per_month
                                ? `${Math.min(100, (orgData.api_requests_this_month / orgData.max_api_requests_per_month) * 100)}%`
                                : '0%',
                            }}
                          />
                        </div>
                      </div>
                    </div>

                    <div className="pt-4 border-t">
                      <Label>Created</Label>
                      <p className="text-sm mt-1">{orgData?.created_at ? new Date(orgData.created_at).toLocaleString() : 'N/A'}</p>
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          )}

          {/* Users Tab */}
          {activeTab === 'users' && (
            <div className="space-y-4">
              {/* Invite User Card */}
              {isAdminOrOwner ? (
                <Card>
                  <CardHeader>
                    <CardTitle>Invite User</CardTitle>
                    <CardDescription>Send an invitation to join your organization</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <Label>Full Name</Label>
                        <Input
                          type="text"
                          value={inviteFullName}
                          onChange={(e) => setInviteFullName(e.target.value)}
                          placeholder="John Doe"
                          className="mt-1"
                        />
                      </div>
                      <div>
                        <Label>Email Address</Label>
                        <Input
                          type="email"
                          value={inviteEmail}
                          onChange={(e) => setInviteEmail(e.target.value)}
                          placeholder="user@example.com"
                          className="mt-1"
                        />
                      </div>
                    </div>
                    <div>
                      <Label>Role</Label>
                      <select
                        value={inviteRole}
                        onChange={(e) => setInviteRole(e.target.value)}
                        className="w-full mt-1 px-3 py-2 border rounded-md"
                      >
                        <option value="viewer">Viewer</option>
                        <option value="member">Member</option>
                        <option value="admin">Admin</option>
                      </select>
                    </div>
                    <Button onClick={handleInviteUser} disabled={isInviting}>
                      {isInviting ? (
                        <>
                          <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                          Sending...
                        </>
                      ) : (
                        <>
                          <Plus className="h-4 w-4 mr-2" />
                          Send Invitation
                        </>
                      )}
                    </Button>
                  </CardContent>
                </Card>
              ) : (
                <Card>
                  <CardHeader>
                    <CardTitle>Invite User</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-muted-foreground">
                      You don't have permission to invite users. Contact your administrator.
                    </p>
                  </CardContent>
                </Card>
              )}

              {/* Users List */}
              <Card>
                <CardHeader>
                  <CardTitle>Team Members</CardTitle>
                  <CardDescription>Manage users in your organization</CardDescription>
                </CardHeader>
                <CardContent>
                  {usersLoading ? (
                    <div className="flex justify-center py-8">
                      <Loader2 className="h-8 w-8 animate-spin text-primary" />
                    </div>
                  ) : usersData?.users.length === 0 ? (
                    <div className="text-center py-8 text-muted-foreground">
                      No users found
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {usersData?.users.map((user) => (
                        <div key={user.user_id} className="flex items-center justify-between p-3 border rounded-lg">
                          <div className="flex-1">
                            <div className="flex items-center gap-2">
                              <p className="font-medium">{user.full_name || user.email}</p>
                              <Badge variant={getRoleBadgeVariant(user.role)}>{user.role}</Badge>
                              {!user.is_active && <Badge variant="secondary">Inactive</Badge>}
                            </div>
                            <p className="text-sm text-muted-foreground">{user.email}</p>
                          </div>
                          <div className="flex items-center gap-2">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleRemoveUser(user.user_id, user.email)}
                              disabled={!isAdminOrOwner || isRemoving || user.role === 'owner'}
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

              {/* Temporary Password Modal */}
              {showPasswordModal && tempPasswordData && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                  <Card className="max-w-md w-full">
                    <CardHeader className="bg-green-50 dark:bg-green-950/20">
                      <CardTitle className="flex items-center text-green-700 dark:text-green-400">
                        <Check className="h-5 w-5 mr-2" />
                        User Invited Successfully
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4 pt-6">
                      <div>
                        <Label>Email</Label>
                        <p className="text-sm font-mono mt-1">{tempPasswordData.email}</p>
                      </div>

                      <div>
                        <Label>Temporary Password</Label>
                        <div className="flex items-center gap-2 mt-1">
                          <code className="flex-1 p-3 bg-gray-100 dark:bg-gray-800 rounded text-sm font-mono">
                            {tempPasswordData.password}
                          </code>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={handleCopyPassword}
                          >
                            {passwordCopied ? (
                              <>
                                <Check className="h-4 w-4 mr-1" />
                                Copied
                              </>
                            ) : (
                              <>
                                <Copy className="h-4 w-4 mr-1" />
                                Copy
                              </>
                            )}
                          </Button>
                        </div>
                      </div>

                      <div className="p-3 bg-yellow-50 dark:bg-yellow-950/20 rounded text-sm">
                        <p className="text-yellow-800 dark:text-yellow-400">
                          <strong>Important:</strong> Share this password securely with the user.
                          They will need to change it on first login. An invitation email has also been sent.
                        </p>
                      </div>

                      <Button onClick={handleCloseModal} className="w-full">
                        Close
                      </Button>
                    </CardContent>
                  </Card>
                </div>
              )}
            </div>
          )}

          {/* API Keys Tab */}
          {activeTab === 'api-keys' && (
            <div className="space-y-4">
              {/* Create API Key Card */}
              {isAdminOrOwner ? (
                <Card>
                  <CardHeader>
                    <CardTitle>Create API Key</CardTitle>
                    <CardDescription>Generate a new API key for programmatic access</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div>
                      <Label>Key Name</Label>
                      <Input
                        value={newKeyName}
                        onChange={(e) => setNewKeyName(e.target.value)}
                        placeholder="Production API Key"
                        className="mt-1"
                      />
                    </div>
                    <Button onClick={handleCreateAPIKey} disabled={isCreatingKey}>
                      {isCreatingKey ? (
                        <>
                          <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                          Generating...
                        </>
                      ) : (
                        <>
                          <Plus className="h-4 w-4 mr-2" />
                          Generate API Key
                        </>
                      )}
                    </Button>

                    {/* Show created key */}
                    {createdKey && (
                      <div className="p-4 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
                        <div className="flex items-start gap-2">
                          <AlertCircle className="h-5 w-5 text-yellow-600 dark:text-yellow-500 mt-0.5" />
                          <div className="flex-1">
                            <p className="font-medium text-yellow-900 dark:text-yellow-100">
                              Save your API key now!
                            </p>
                            <p className="text-sm text-yellow-700 dark:text-yellow-300 mt-1">
                              You won't be able to see it again. Store it securely.
                            </p>
                            <div className="mt-3 flex items-center gap-2">
                              <code className="flex-1 p-2 bg-white dark:bg-slate-900 rounded border font-mono text-sm break-all">
                                {createdKey}
                              </code>
                              <Button variant="outline" size="sm" onClick={handleCopyKey}>
                                {copiedKey ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                              </Button>
                            </div>
                          </div>
                        </div>
                      </div>
                    )}
                  </CardContent>
                </Card>
              ) : (
                <Card>
                  <CardHeader>
                    <CardTitle>Create API Key</CardTitle>
                    <CardDescription>Generate a new API key for programmatic access</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="p-4 bg-muted rounded-lg">
                      <p className="text-sm text-muted-foreground">
                        You don't have permission to create API keys. Contact your organization administrator.
                      </p>
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* API Keys List */}
              <Card>
                <CardHeader>
                  <CardTitle>API Keys</CardTitle>
                  <CardDescription>Manage your API keys</CardDescription>
                </CardHeader>
                <CardContent>
                  {keysLoading ? (
                    <div className="flex justify-center py-8">
                      <Loader2 className="h-8 w-8 animate-spin text-primary" />
                    </div>
                  ) : keysData?.api_keys.length === 0 ? (
                    <div className="text-center py-8 text-muted-foreground">
                      No API keys found
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {keysData?.api_keys.map((key) => (
                        <div key={key.key_id} className="flex items-center justify-between p-3 border rounded-lg">
                          <div className="flex-1">
                            <div className="flex items-center gap-2">
                              <p className="font-medium">{key.key_name || 'Unnamed Key'}</p>
                              {key.is_active ? (
                                <Badge variant="success">Active</Badge>
                              ) : (
                                <Badge variant="secondary">Revoked</Badge>
                              )}
                            </div>
                            <p className="text-sm font-mono text-muted-foreground">{key.key_prefix}</p>
                            <p className="text-xs text-muted-foreground mt-1">
                              Created: {new Date(key.created_at).toLocaleDateString()}
                              {key.last_used_at && ` • Last used: ${new Date(key.last_used_at).toLocaleDateString()}`}
                            </p>
                          </div>
                          <div className="flex items-center gap-2">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleRevokeAPIKey(key.key_id, key.key_name || '')}
                              disabled={isRevokingKey || !key.is_active || !isAdminOrOwner}
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
          )}

          {/* Security Tab */}
          {activeTab === 'security' && (
            <div className="space-y-4">
              {/* Password Change Section */}
              <Card>
                <CardHeader>
                  <CardTitle>Change Password</CardTitle>
                  <CardDescription>
                    Update your account password. Make sure to use a strong password with at least 8 characters.
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <Button
                    onClick={() => navigate('/change-password')}
                    className="w-full sm:w-auto"
                  >
                    <Shield className="h-4 w-4 mr-2" />
                    Change Password
                  </Button>
                  <p className="text-sm text-muted-foreground mt-4">
                    You'll be redirected to a secure page to change your password.
                  </p>
                </CardContent>
              </Card>

              {/* Account Security Info */}
              <Card>
                <CardHeader>
                  <CardTitle>Account Security</CardTitle>
                  <CardDescription>
                    Security recommendations for your account
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="flex items-start gap-3 p-3 bg-muted rounded-lg">
                    <AlertCircle className="h-5 w-5 text-muted-foreground shrink-0 mt-0.5" />
                    <div className="space-y-1">
                      <p className="text-sm font-medium">Strong Password</p>
                      <p className="text-sm text-muted-foreground">
                        Use a password with at least 8 characters, including uppercase, lowercase, and numbers.
                      </p>
                    </div>
                  </div>
                  <div className="flex items-start gap-3 p-3 bg-muted rounded-lg">
                    <AlertCircle className="h-5 w-5 text-muted-foreground shrink-0 mt-0.5" />
                    <div className="space-y-1">
                      <p className="text-sm font-medium">Regular Updates</p>
                      <p className="text-sm text-muted-foreground">
                        Change your password regularly and never reuse passwords across different services.
                      </p>
                    </div>
                  </div>
                  <div className="flex items-start gap-3 p-3 bg-muted rounded-lg">
                    <AlertCircle className="h-5 w-5 text-muted-foreground shrink-0 mt-0.5" />
                    <div className="space-y-1">
                      <p className="text-sm font-medium">Temporary Passwords</p>
                      <p className="text-sm text-muted-foreground">
                        If you received a temporary password during invitation, make sure to change it immediately.
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}

          {/* Integrations Tab */}
          {activeTab === 'integrations' && (
            <div className="space-y-6">
              {/* Slack Integration */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center">
                    <MessageSquare className="h-5 w-5 mr-2" />
                    Slack Integration
                  </CardTitle>
                  <CardDescription>
                    Receive security alerts directly in Slack
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {showSlackSetup ? (
                    <SlackSetupWizard onComplete={() => setShowSlackSetup(false)} />
                  ) : (
                    <div className="space-y-4">
                      <p className="text-sm text-muted-foreground">
                        Connect your Slack workspace to receive real-time security alerts and threat notifications.
                      </p>
                      <Button onClick={() => setShowSlackSetup(true)}>
                        <MessageSquare className="h-4 w-4 mr-2" />
                        Setup Slack Integration
                      </Button>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Webhooks */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center">
                    <Zap className="h-5 w-5 mr-2" />
                    Webhooks
                  </CardTitle>
                  <CardDescription>
                    Send security events to external systems
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <WebhookConfig />
                </CardContent>
              </Card>
            </div>
          )}
          </div>
          </div>
          </div>
          );
          }
