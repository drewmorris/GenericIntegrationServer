// @ts-nocheck
import { Routes, Route, Navigate } from 'react-router-dom';
import Login from './Login';
import { Typography } from '@mui/material';
import { useAuth } from '../context/AuthContext';
import ProfilesList from './ProfilesList';
import ProfileWizard from './ProfileWizard';
import TopNav from '../components/TopNav';
import SyncRunsPage from './SyncRunsPage';
import ProfileEdit from './ProfileEdit';
import { useDashboardStats } from '../hooks/useDashboardStats';

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
                <Route path="/" element={accessToken ? <Dashboard /> : <Navigate to="/login" />} />
                <Route path="/profiles" element={accessToken ? <ProfilesList /> : <Navigate to="/login" />} />
                <Route path="/profiles/new" element={accessToken ? <ProfileWizard /> : <Navigate to="/login" />} />
                <Route path="/profiles/:id/runs" element={accessToken ? <SyncRunsPage /> : <Navigate to="/login" />} />
                <Route path="/profiles/:id/edit" element={accessToken ? <ProfileEdit /> : <Navigate to="/login" />} />
                <Route path="*" element={<Navigate to="/" />} />
            </Routes>
        </>
    );
} 