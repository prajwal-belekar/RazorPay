import { Agent, AgentActivityLog } from '@/types';
import { apiFetch } from './client';
import { mockAgents, mockAgentActivityStream } from '../mock/agents';

export async function getAgents(): Promise<Agent[]> {
  try {
    return await apiFetch<Agent[]>('/api/agents');
  } catch {
    return mockAgents;
  }
}

export async function getAgentActivity(): Promise<AgentActivityLog[]> {
  try {
    return await apiFetch<AgentActivityLog[]>('/api/agents/activity');
  } catch {
    return mockAgentActivityStream;
  }
}
