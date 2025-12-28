import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useOrganization, useOrganizationUsers, useInviteUser, useRemoveUser } from '@/hooks/useOrganizations';
import { useAPIKeys, useCreateAPIKey, useRevokeAPIKey } from '@/hooks/useAPIKeys';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Shield, Users, Key, Plus, Trash2, Loader2, AlertCircle, Copy, Check } from 'lucide-react';
import { cn } from '@/lib/utils';

export function SettingsPage() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<'organization' | 'users' | 'api-keys'>('organization');
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState('member');
  const [newKeyName, setNewKeyName] = useState('');
  const [createdKey, setCreatedKey] = useState<string | null>(null);
  const [copiedKey, setCopiedKey] = useState(false);

  const { data: orgData, isLoading: orgLoading } = useOrganization();
  const { data: usersData, isLoading: usersLoading } = useOrganizationUsers();
  const { data: keysData, isLoading: keysLoading } = useAPIKeys();

  const { mutate: inviteUser, isPending: isInviting } = useInviteUser();
  const { mutate: removeUser, isPending: isRemoving } = useRemoveUser();
  const { mutate: createAPIKey, isPending: isCreatingKey } = useCreateAPIKey();
  const { mutate: revokeAPIKey, isPending: isRevokingKey } = useRevokeAPIKey();

  const handleInviteUser = () => {
    if (!inviteEmail.trim()) {
      alert('Please enter an email address');
      return;
    }

    inviteUser(
      { email: inviteEmail, role: inviteRole },
      {
        onSuccess: () => {
          setInviteEmail('');
          alert('User invited successfully');
        },
        onError: (error: any) => {
          alert(`Failed to invite user: ${error.response?.data?.detail || error.message}`);
        },
      }
    );
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
              <Card>
                <CardHeader>
                  <CardTitle>Invite User</CardTitle>
                  <CardDescription>Send an invitation to join your organization</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
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
                              disabled={isRemoving || user.role === 'owner'}
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

          {/* API Keys Tab */}
          {activeTab === 'api-keys' && (
            <div className="space-y-4">
              {/* Create API Key Card */}
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
                              disabled={isRevokingKey || !key.is_active}
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
        </div>
      </div>
    </div>
  );
}
