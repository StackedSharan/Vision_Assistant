import { BrowserRouter as Router, Routes, Route, useLocation } from 'react-router-dom';
import LandingPage from './components/LandingPage';
import Dashboard from './components/Dashboard';
import Calibration from './components/Calibration';
import ChatBox from './components/ChatBox';
import './App.css';

function AppContent() {
  const location = useLocation();
  const showChatBox = location.pathname !== '/dashboard';

  return (
    <>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/calibrate" element={<Calibration />} />
      </Routes>
      {showChatBox && <ChatBox />}
    </>
  );
}

function App() {
  return (
    <Router>
      <AppContent />
    </Router>
  );
}

export default App;