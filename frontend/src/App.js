import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import LandingPage from './components/LandingPage';
import Dashboard from './components/Dashboard';
import Calibration from './components/Calibration';
import ChatBox from './components/ChatBox';
import './App.css';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/calibrate" element={<Calibration />} />
      </Routes>
      <ChatBox />
    </Router>
  );
}

export default App;