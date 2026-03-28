import { Routes, Route, useLocation } from 'react-router-dom';
import { AnimatePresence } from 'framer-motion';
import { Sidebar } from './components/layout/Sidebar';
import { ErrorBoundary } from './components/ui/ErrorBoundary';
import Landing from './pages/Landing';
import Dashboard from './pages/Dashboard';
import ICPSetup from './pages/ICPSetup';
import PipelineRun from './pages/PipelineRun';
import Prospects from './pages/Prospects';
import Research from './pages/Research';
import Outreach from './pages/Outreach';
import Tracking from './pages/Tracking';
import Settings from './pages/Settings';

export default function App() {
  const location = useLocation();
  const isLanding = location.pathname === '/';

  if (isLanding) {
    return (
      <AnimatePresence mode="wait">
        <Routes location={location} key={location.pathname}>
          <Route path="/" element={<Landing />} />
        </Routes>
      </AnimatePresence>
    );
  }

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 min-w-0">
        <ErrorBoundary>
          <AnimatePresence mode="wait">
            <Routes location={location} key={location.pathname}>
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/icp" element={<ICPSetup />} />
              <Route path="/pipeline-run" element={<PipelineRun />} />
              <Route path="/prospects" element={<Prospects />} />
              <Route path="/research" element={<Research />} />
              <Route path="/outreach" element={<Outreach />} />
              <Route path="/tracking" element={<Tracking />} />
              <Route path="/settings" element={<Settings />} />
            </Routes>
          </AnimatePresence>
        </ErrorBoundary>
      </main>
    </div>
  );
}
