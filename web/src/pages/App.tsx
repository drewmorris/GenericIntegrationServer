// @ts-nocheck
import { useEffect, useState } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import { AuthLoadingSpinner } from '../components/AuthLoadingSpinner';
import ImprovedTopNav from '../components/ImprovedTopNav';
import { useAuth } from '../context/AuthContext';
import { useGlobalErrorHandler } from '../hooks/useGlobalErrorHandler';
import ConnectorsPage from './Connectors';
import DashboardPage from './DashboardPage';
import DestinationsPage from './Destinations';
import Login from './Login';
import ProfileEdit from './ProfileEdit';
import ProfilesList from './ProfilesList';
import ProfileWizard from './ProfileWizard';
import Signup from './Signup';
import SyncMonitoringPage from './SyncMonitoringPage';
import SyncRunsPage from './SyncRunsPage';

export default function App() {
  const { isAuthenticated } = useAuth();
  const [isInitializing, setIsInitializing] = useState(true);

  // Initialize global error handling
  useGlobalErrorHandler();

  // Handle initial authentication state loading
  useEffect(() => {
    // Give a moment for authentication state to stabilize
    const timer = setTimeout(() => {
      setIsInitializing(false);
    }, 100);

    return () => clearTimeout(timer);
  }, []);

  // Show loading spinner during initial auth check
  if (isInitializing) {
    return <AuthLoadingSpinner message="Loading application..." />;
  }

  return (
    <>
      {isAuthenticated && <ImprovedTopNav />}
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />
        <Route path="/" element={isAuthenticated ? <DashboardPage /> : <Navigate to="/login" />} />
        <Route
          path="/profiles"
          element={isAuthenticated ? <ProfilesList /> : <Navigate to="/login" />}
        />
        <Route
          path="/profiles/new"
          element={isAuthenticated ? <ProfileWizard /> : <Navigate to="/login" />}
        />
        <Route
          path="/profiles/:id/runs"
          element={isAuthenticated ? <SyncRunsPage /> : <Navigate to="/login" />}
        />
        <Route
          path="/profiles/:id/edit"
          element={isAuthenticated ? <ProfileEdit /> : <Navigate to="/login" />}
        />
        <Route
          path="/destinations"
          element={isAuthenticated ? <DestinationsPage /> : <Navigate to="/login" />}
        />
        <Route
          path="/connectors"
          element={isAuthenticated ? <ConnectorsPage /> : <Navigate to="/login" />}
        />
        <Route
          path="/sync-monitoring"
          element={isAuthenticated ? <SyncMonitoringPage /> : <Navigate to="/login" />}
        />

        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </>
  );
}
