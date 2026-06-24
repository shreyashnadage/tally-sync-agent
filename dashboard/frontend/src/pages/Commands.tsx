import React, { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import axios from 'axios';

export default function Commands() {
  const { company_guid } = useParams<{ company_guid: string }>();
  const [commandType, setCommandType] = useState('TRIGGER_SYNC');
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  async function sendCommand() {
    setLoading(true);
    setError(null);
    setResponse(null);

    try {
      const res = await axios.post('/api/commands', {
        company_guid,
        command_type: commandType,
        payload: {}
      });
      setResponse(res.data);
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to send command');
    } finally {
      setLoading(false);
    }
  }

  const commandDescriptions: Record<string, string> = {
    TRIGGER_SYNC: 'Start an immediate sync on the agent',
    FETCH_VOUCHER: 'Fetch a specific voucher from Tally',
    FETCH_LEDGER_BALANCE: 'Get real-time ledger balance',
    HEALTH_CHECK: 'Get agent health status and connectivity',
    CONFIG_SYNC: 'Fetch updated configuration from cloud'
  };

  return (
    <div className="space-y-8">
      <div>
        <Link to={`/agent/${company_guid}`} className="text-blue-600 hover:text-blue-900">← Back to Agent</Link>
        <h1 className="text-3xl font-bold text-gray-900 mt-2">Send Command</h1>
      </div>

      <div className="card">
        <div className="card-body space-y-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Command Type
            </label>
            <select
              value={commandType}
              onChange={(e) => setCommandType(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="TRIGGER_SYNC">Trigger Sync</option>
              <option value="FETCH_VOUCHER">Fetch Voucher</option>
              <option value="FETCH_LEDGER_BALANCE">Fetch Ledger Balance</option>
              <option value="HEALTH_CHECK">Health Check</option>
              <option value="CONFIG_SYNC">Config Sync</option>
            </select>
            <p className="mt-2 text-sm text-gray-600">{commandDescriptions[commandType]}</p>
          </div>

          <button
            onClick={sendCommand}
            disabled={loading}
            className="btn disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Sending...' : 'Send Command'}
          </button>
        </div>
      </div>

      {error && (
        <div className="card border-l-4 border-red-500">
          <div className="card-body">
            <p className="text-red-600"><strong>Error:</strong> {error}</p>
          </div>
        </div>
      )}

      {response && (
        <div className="card border-l-4 border-green-500">
          <div className="card-body">
            <p className="text-green-600 font-medium mb-2">✓ Command Sent Successfully</p>
            <pre className="bg-gray-50 p-4 rounded text-sm overflow-auto text-gray-900">
              {JSON.stringify(response, null, 2)}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}
