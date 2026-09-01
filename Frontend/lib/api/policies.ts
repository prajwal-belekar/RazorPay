import { PolicySet } from '@/types';
import { apiFetch } from './client';
import { mockPolicySet } from '../mock/policies';

export async function getPolicies(): Promise<PolicySet> {
  try {
    return await apiFetch<PolicySet>('/api/policies');
  } catch {
    return mockPolicySet;
  }
}

export async function updatePolicies(updatedRules: PolicySet['rules']): Promise<PolicySet> {
  try {
    return await apiFetch<PolicySet>('/api/policies', {
      method: 'PUT',
      body: JSON.stringify({ rules: updatedRules }),
    });
  } catch {
    const versionParts = mockPolicySet.version.replace('v', '').split('.');
    const newMinor = parseInt(versionParts[1] || '0') + 1;
    const newVersion = `v${versionParts[0]}.${newMinor}`;

    return {
      ...mockPolicySet,
      version: newVersion,
      rules: updatedRules,
      lastUpdated: new Date().toISOString(),
      hash: `0x${Math.random().toString(16).substring(2, 10)}${Math.random().toString(16).substring(2, 10)}`,
    };
  }
}
