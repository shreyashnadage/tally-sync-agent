import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import './styles/index.css';
import Dashboard from './pages/Dashboard';
import AgentDetail from './pages/AgentDetail';
import SyncHistory from './pages/SyncHistory';
import Commands from './pages/Commands';
import Navbar from './components/Navbar';

export default function App() {
  return (
    <Router>
      <div className="min-h-screen bg-gray-50">
        <Navbar />
        <main className="max-w-7xl mx-auto px-4 py-8">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/agent/:company_guid" element={<AgentDetail />} />
            <Route path="/agent/:company_guid/sync-history" element={<SyncHistory />} />
            <Route path="/agent/:company_guid/commands" element={<Commands />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}
