// @ts-nocheck
import { Typography } from '@mui/material';
import { Navigate, Route, Routes } from 'react-router-dom';

import TopNav from '../components/TopNav';
import { useAuth } from '../context/AuthContext';
import { useDashboardStats } from '../hooks/useDashboardStats';
import ConnectorsPage from './Connectors';
import DestinationsPage from './Destinations';
import Login from './Login';
import ProfileEdit from './ProfileEdit';
import ProfilesList from './ProfilesList';
import ProfileWizard from './ProfileWizard';
import Signup from './Signup';
import SyncRunsPage from './SyncRunsPage';

function Dashboard() {
  const { totalProfiles } = useDashboardStats();
  return (
    <Typography variant="h5" sx={{ mt: 4, ml: 2 }}>
      You have {totalProfiles} connector {totalProfiles === 1 ? 'profile' : 'profiles'}.
    </Typography>
  );
}

export default function App() {
  const { accessToken } = useAuth();
  return (
    <>
      {accessToken && <TopNav />}
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />
        <Route path="/" element={accessToken ? <Dashboard /> : <Navigate to="/login" />} />
        <Route
          path="/profiles"
          element={accessToken ? <ProfilesList /> : <Navigate to="/login" />}
        />
        <Route
          path="/profiles/new"
          element={accessToken ? <ProfileWizard /> : <Navigate to="/login" />}
        />
        <Route
          path="/profiles/:id/runs"
          element={accessToken ? <SyncRunsPage /> : <Navigate to="/login" />}
        />
        <Route
          path="/profiles/:id/edit"
          element={accessToken ? <ProfileEdit /> : <Navigate to="/login" />}
        />
        <Route
          path="/destinations"
          element={accessToken ? <DestinationsPage /> : <Navigate to="/login" />}
        />
        <Route
          path="/connectors"
          element={accessToken ? <ConnectorsPage /> : <Navigate to="/login" />}
        />

        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </>
  );
}
