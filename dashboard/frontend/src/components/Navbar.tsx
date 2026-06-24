import React from 'react';
import { Link } from 'react-router-dom';

export default function Navbar() {
  return (
    <nav className="bg-white shadow">
      <div className="max-w-7xl mx-auto px-4">
        <div className="flex justify-between items-center h-16">
          <Link to="/" className="flex items-center space-x-2">
            <div className="text-2xl font-bold text-blue-600">TB</div>
            <div>
              <div className="text-lg font-bold text-gray-900">TallyBridge</div>
              <div className="text-xs text-gray-500">Agent Control Panel</div>
            </div>
          </Link>

          <div className="flex items-center space-x-4">
            <Link
              to="/"
              className="px-3 py-2 rounded-md text-sm font-medium text-gray-700 hover:text-gray-900 hover:bg-gray-50"
            >
              Dashboard
            </Link>
            <div className="text-sm text-gray-500">
              v0.1.0
            </div>
          </div>
        </div>
      </div>
    </nav>
  );
}
