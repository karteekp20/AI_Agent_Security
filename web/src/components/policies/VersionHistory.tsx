import React, { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { apiClient } from '../../api/client';

// Simple date formatter (replacing date-fns to avoid dependency)
const formatDistanceToNow = (date: string): string => {
  const now = new Date();
  const then = new Date(date);
  const seconds = Math.floor((now.getTime() - then.getTime()) / 1000);
  
  if (seconds < 60) return 'just now';
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  if (seconds < 604800) return `${Math.floor(seconds / 86400)}d ago`;
  return then.toLocaleDateString();
};

interface PolicyVersion {
  policyId: string;
  version: number;
  status: 'draft' | 'testing' | 'active' | 'archived';
  createdAt: string;
  createdBy: string;
  commitMessage: string;
}

interface VersionHistoryProps {
  policyId: string;
  onVersionSelect: (version: PolicyVersion) => void;
  onRollback: (targetVersion: number) => void;
}

const fetchPolicyVersions = async (policyId: string): Promise<PolicyVersion[]> => {
  try {
    const response = await apiClient.get(
      `/policies/${policyId}/versions`
    );
    return Array.isArray(response.data) ? response.data : response.data.versions || [];
  } catch (error) {
    console.error('Error fetching versions:', error);
    return [];
  }
};

const rollbackPolicy = async (policyId: string, targetVersion: number): Promise<void> => {
  await apiClient.post(`/policies/${policyId}/versions/${targetVersion}/rollback`, {});
};

export const VersionHistory: React.FC<VersionHistoryProps> = ({
  policyId,
  onVersionSelect,
  onRollback,
}) => {
  const [selectedVersions, setSelectedVersions] = useState<string[]>([]);

  const { data: versions = [] } = useQuery({
    queryKey: ['policyVersions', policyId],
    queryFn: () => fetchPolicyVersions(policyId),
  });

  const rollbackMutation = useMutation({
    mutationFn: (targetVersion: number) =>
      rollbackPolicy(policyId, targetVersion),
    onSuccess: () => {
      // Invalidate queries to refresh
    },
  });

  const handleCompare = () => {
    if (selectedVersions.length === 2) {
      // Navigate to diff view
      window.location.href =
        `/policies/diff?a=${selectedVersions[0]}&b=${selectedVersions[1]}`;
    }
  };

  const statusColors = {
    draft: 'bg-gray-100 text-gray-700',
    testing: 'bg-yellow-100 text-yellow-700',
    active: 'bg-green-100 text-green-700',
    archived: 'bg-red-100 text-red-700',
  };

  return (
    <div className="version-history">
      <div className="version-header">
        <h3>Version History</h3>
        {selectedVersions.length === 2 && (
          <button onClick={handleCompare} className="btn-compare">
            Compare Selected
          </button>
        )}
      </div>

      <div className="version-list">
         {versions?.map((version: PolicyVersion, index: number) => (
          <div
            key={version.policyId}
            className={`version-item ${
              selectedVersions.includes(version.policyId) ? 'selected' : ''
            }`}
          >
            <input
              type="checkbox"
              checked={selectedVersions.includes(version.policyId)}
              onChange={(e) => {
                if (e.target.checked && selectedVersions.length < 2) {
                  setSelectedVersions([...selectedVersions, version.policyId]);
                } else {
                  setSelectedVersions(
                    selectedVersions.filter(id => id !== version.policyId)
                  );
                }
              }}
            />

            <div className="version-info" onClick={() => onVersionSelect(version)}>
              <div className="version-number">
                v{version.version}
                {index === 0 && <span className="current-badge">Current</span>}
              </div>

              <span className={`status-badge ${statusColors[version.status as keyof typeof statusColors]}`}>
                {version.status}
              </span>

              <div className="version-meta">
                <span className="commit-message">{version.commitMessage}</span>
                <span className="timestamp">
                   {formatDistanceToNow(version.createdAt)} ago
                </span>
                <span className="author">by {version.createdBy}</span>
              </div>
            </div>

            {version.status !== 'active' && (
              <button
                className="btn-rollback"
                onClick={() => onRollback(version.version)}
                disabled={rollbackMutation.isPending}
              >
                Rollback
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};