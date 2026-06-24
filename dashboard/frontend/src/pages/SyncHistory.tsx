import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import axios from 'axios';

export default function SyncHistory() {
  const { company_guid } = useParams<{ company_guid: string }>();
  const [syncs, setSyncs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSyncHistory();
  }, [company_guid]);

  async function fetchSyncHistory() {
    try {
      const response = await axios.get(`/api/sync/history/${company_guid}`);
      setSyncs(response.data.syncs);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching sync history:', error);
      setLoading(false);
    }
  }

  return (
    <div className="space-y-8">
      <div>
        <Link to={`/agent/${company_guid}`} className="text-blue-600 hover:text-blue-900">← Back to Agent</Link>
        <h1 className="text-3xl font-bold text-gray-900 mt-2">Sync History</h1>
      </div>

      <div className="card">
        {loading ? (
          <div className="card-body text-center text-gray-500">Loading sync history...</div>
        ) : syncs.length === 0 ? (
          <div className="card-body text-center text-gray-500">No syncs recorded yet</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="border-b border-gray-200 bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Records</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Duration</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {syncs.map((sync: any) => (
                  <tr key={sync.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 text-sm text-gray-900">
                      {new Date(sync.completed_at).toLocaleString()}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500">{sync.sync_type}</td>
                    <td className="px-6 py-4 text-sm text-gray-500">{sync.records_synced}</td>
                    <td className="px-6 py-4 text-sm text-gray-500">{Math.round(sync.duration_ms)}ms</td>
                    <td className="px-6 py-4 text-sm">
                      <span className={`badge ${sync.status === 'SUCCESS' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                        {sync.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
