import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import axios from 'axios';

interface AgentData {
  agent: any;
  statistics: any;
  recent_syncs: any[];
}

export default function AgentDetail() {
  const { company_guid } = useParams<{ company_guid: string }>();
  const [agent, setAgent] = useState<AgentData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAgentDetails();
  }, [company_guid]);

  async function fetchAgentDetails() {
    try {
      const response = await axios.get(`/api/agents/${company_guid}`);
      setAgent(response.data);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching agent details:', error);
      setLoading(false);
    }
  }

  if (loading) return <div className="text-center py-8">Loading agent details...</div>;
  if (!agent) return <div className="text-center py-8">Agent not found</div>;

  const { agent: agentInfo, statistics } = agent;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <Link to="/" className="text-blue-600 hover:text-blue-900">← Back to Dashboard</Link>
          <h1 className="text-3xl font-bold text-gray-900 mt-2">{agentInfo.company_name}</h1>
          <p className="text-gray-600">{agentInfo.company_guid}</p>
        </div>
        <div className={`badge text-lg ${agentInfo.status === 'ACTIVE' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}`}>
          {agentInfo.status}
        </div>
      </div>

      {/* Agent Info Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="card">
          <div className="card-body">
            <div className="text-sm font-medium text-gray-500">Tally Version</div>
            <div className="mt-2 text-lg font-semibold text-gray-900">{agentInfo.tally_version || 'Unknown'}</div>
          </div>
        </div>
        <div className="card">
          <div className="card-body">
            <div className="text-sm font-medium text-gray-500">Agent Version</div>
            <div className="mt-2 text-lg font-semibold text-gray-900">{agentInfo.agent_version || 'Unknown'}</div>
          </div>
        </div>
        <div className="card">
          <div className="card-body">
            <div className="text-sm font-medium text-gray-500">Last Seen</div>
            <div className="mt-2 text-lg font-semibold text-gray-900">
              {agentInfo.last_seen_at ? new Date(agentInfo.last_seen_at).toLocaleString() : 'Never'}
            </div>
          </div>
        </div>
      </div>

      {/* Statistics */}
      {statistics && (
        <div className="card">
          <div className="card-header">
            <h2 className="text-lg font-semibold text-gray-900">Sync Statistics</h2>
          </div>
          <div className="card-body">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <div className="text-sm text-gray-600">Total Syncs</div>
                <div className="text-2xl font-bold text-gray-900">{statistics.total_syncs || 0}</div>
              </div>
              <div>
                <div className="text-sm text-gray-600">Successful</div>
                <div className="text-2xl font-bold text-green-600">{statistics.successful_syncs || 0}</div>
              </div>
              <div>
                <div className="text-sm text-gray-600">Failed</div>
                <div className="text-2xl font-bold text-red-600">{statistics.failed_syncs || 0}</div>
              </div>
              <div>
                <div className="text-sm text-gray-600">Avg Duration</div>
                <div className="text-2xl font-bold text-gray-900">{Math.round(statistics.avg_duration_ms || 0)}ms</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex space-x-4">
        <Link
          to={`/agent/${company_guid}/sync-history`}
          className="btn"
        >
          View Sync History
        </Link>
        <Link
          to={`/agent/${company_guid}/commands`}
          className="btn"
        >
          Send Command
        </Link>
      </div>
    </div>
  );
}
