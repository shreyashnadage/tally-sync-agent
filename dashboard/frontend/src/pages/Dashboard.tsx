import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';

interface Agent {
  id: string;
  company_name: string;
  company_guid: string;
  tally_version: string;
  agent_version: string;
  status: string;
  last_seen_at: string;
  created_at: string;
  total_syncs?: number;
  last_sync_at?: string;
}

export default function Dashboard() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    total_agents: 0,
    active_agents: 0,
    inactive_agents: 0,
    error_agents: 0
  });

  useEffect(() => {
    fetchAgents();
    fetchStats();
  }, []);

  async function fetchAgents() {
    try {
      const response = await axios.get('/api/agents');
      setAgents(response.data.agents);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching agents:', error);
      setLoading(false);
    }
  }

  async function fetchStats() {
    try {
      const response = await axios.get('/api/health/agents');
      setStats(response.data);
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'ACTIVE':
        return 'bg-green-100 text-green-800';
      case 'INACTIVE':
        return 'bg-gray-100 text-gray-800';
      case 'ERROR':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
        <p className="mt-2 text-gray-600">Manage and monitor all connected TallyBridge agents</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="card">
          <div className="card-body">
            <div className="text-sm font-medium text-gray-500">Total Agents</div>
            <div className="mt-2 text-3xl font-bold text-gray-900">{stats.total_agents}</div>
          </div>
        </div>
        <div className="card">
          <div className="card-body">
            <div className="text-sm font-medium text-green-600">Active</div>
            <div className="mt-2 text-3xl font-bold text-green-600">{stats.active_agents}</div>
          </div>
        </div>
        <div className="card">
          <div className="card-body">
            <div className="text-sm font-medium text-gray-600">Inactive</div>
            <div className="mt-2 text-3xl font-bold text-gray-600">{stats.inactive_agents}</div>
          </div>
        </div>
        <div className="card">
          <div className="card-body">
            <div className="text-sm font-medium text-red-600">Errors</div>
            <div className="mt-2 text-3xl font-bold text-red-600">{stats.error_agents}</div>
          </div>
        </div>
      </div>

      {/* Agents List */}
      <div className="card">
        <div className="card-header">
          <h2 className="text-lg font-semibold text-gray-900">Connected Agents</h2>
        </div>
        <div className="overflow-x-auto">
          {loading ? (
            <div className="card-body text-center text-gray-500">Loading agents...</div>
          ) : agents.length === 0 ? (
            <div className="card-body text-center text-gray-500">No agents connected yet</div>
          ) : (
            <table className="w-full">
              <thead className="border-b border-gray-200 bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Company</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Tally Version</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Agent Version</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Last Sync</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {agents.map((agent) => (
                  <tr key={agent.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 text-sm font-medium text-gray-900">{agent.company_name}</td>
                    <td className="px-6 py-4 text-sm">
                      <span className={`badge ${getStatusColor(agent.status)}`}>
                        {agent.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500">{agent.tally_version || 'Unknown'}</td>
                    <td className="px-6 py-4 text-sm text-gray-500">{agent.agent_version || 'Unknown'}</td>
                    <td className="px-6 py-4 text-sm text-gray-500">
                      {agent.last_sync_at ? new Date(agent.last_sync_at).toLocaleString() : 'Never'}
                    </td>
                    <td className="px-6 py-4 text-sm">
                      <Link
                        to={`/agent/${agent.company_guid}`}
                        className="text-blue-600 hover:text-blue-900 font-medium"
                      >
                        View →
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
