import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Navbar from './components/Navbar'; // Refers to 10. Navbar.js structure
import TopicsPage from './features/student/TopicsPage';
import AdminDraftsPage from './features/admin/AdminDraftsPage';
import './styles/App.css';

function App() {
  return (
    <Router>
      <div className="app-wrapper">
        <Navbar />
        <main className="main-content">
          <Routes>
            {/* Automatic redirection down to landing views */}
            <Route path="/" element={<Navigate to="/topics" replace />} />
            <Route path="/topics" element={<TopicsPage />} />
            <Route path="/admin/drafts" element={<AdminDraftsPage />} />
            {/* Fallback route mismatch protection rule */}
            <Route path="*" element={<Navigate to="/topics" replace />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;