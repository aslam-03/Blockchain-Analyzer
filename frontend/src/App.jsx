import { BrowserRouter, Navigate, Route, Routes, useNavigate } from 'react-router-dom';
import IntroPage from './components/IntroPage';
import DashboardPage from './pages/DashboardPage';

function IntroRoute() {
  const navigate = useNavigate();
  return <IntroPage onEnter={() => navigate('/app')} />;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<IntroRoute />} />
        <Route path="/app" element={<DashboardPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
