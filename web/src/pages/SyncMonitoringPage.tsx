/**
 * SyncMonitoringPage - Real-time sync monitoring dashboard
 * Shows active syncs with progress bars and allows management
 */

import {
  Cable as CableIcon,
  Pause as PauseIcon,
  PlayArrow as PlayIcon,
  Refresh as RefreshIcon,
  Send as SendIcon,
  Timeline as TimelineIcon,
} from '@mui/icons-material';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Grid,
  Stack,
  Tab,
  Tabs,
  Typography,
  useTheme,
} from '@mui/material';
import { useQuery } from '@tanstack/react-query';
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { SyncProgressCard } from '../components/SyncProgressCard';
import { useActiveSyncs } from '../hooks/useActiveSyncs';
import { api } from '../lib/api';

interface DashboardStats {
  total_cc_pairs: number;
}

const SyncMonitoringPage: React.FC = () => {
  const theme = useTheme();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState(0);
  const { data: activeSyncs, isLoading, error, refetch, isRefetching } = useActiveSyncs();

  // Fetch basic stats for empty state guidance
  const { data: stats } = useQuery<DashboardStats>({
    queryKey: ['sync-monitor-stats'],
    queryFn: async () => {
      const ccPairs = await api.get('/cc-pairs/');
      return {
        total_cc_pairs: ccPairs.data?.length || 0,
      };
    },
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
  });

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
  };

  const handleRefresh = () => {
    refetch();
  };

  // Filter syncs by status for different tabs
  const inProgressSyncs = activeSyncs?.filter((sync) => sync.status === 'IN_PROGRESS') || [];
  const completedSyncs =
    activeSyncs?.filter(
      (sync) => sync.status === 'SUCCESS' || sync.status === 'FAILED' || sync.status === 'CANCELED',
    ) || [];

  const getStatusCounts = () => {
    const counts = {
      in_progress: 0,
      success: 0,
      failed: 0,
      canceled: 0,
    };

    activeSyncs?.forEach((sync) => {
      switch (sync.status) {
        case 'IN_PROGRESS':
          counts.in_progress++;
          break;
        case 'SUCCESS':
          counts.success++;
          break;
        case 'FAILED':
          counts.failed++;
          break;
        case 'CANCELED':
          counts.canceled++;
          break;
      }
    });

    return counts;
  };

  const statusCounts = getStatusCounts();

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Box>
          <Typography variant="h4" gutterBottom>
            Sync Monitoring
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Real-time monitoring of sync operations with progress tracking
          </Typography>
        </Box>

        <Button
          variant="outlined"
          startIcon={<RefreshIcon />}
          onClick={handleRefresh}
          disabled={isRefetching}
        >
          {isRefetching ? 'Refreshing...' : 'Refresh'}
        </Button>
      </Box>

      {/* Status Overview Cards */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography variant="h4" color="primary.main">
                    {statusCounts.in_progress}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Active Syncs
                  </Typography>
                </Box>
                <PlayIcon color="primary" fontSize="large" />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography variant="h4" color="success.main">
                    {statusCounts.success}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Completed
                  </Typography>
                </Box>
                <TimelineIcon color="success" fontSize="large" />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography variant="h4" color="error.main">
                    {statusCounts.failed}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Failed
                  </Typography>
                </Box>
                <PauseIcon color="error" fontSize="large" />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography variant="h4" color="warning.main">
                    {statusCounts.canceled}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Canceled
                  </Typography>
                </Box>
                <PauseIcon color="warning" fontSize="large" />
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Error handling */}
      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          Failed to load sync data: {error.message}
        </Alert>
      )}

      {/* Tabs for different sync views */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
        <Tabs value={activeTab} onChange={handleTabChange}>
          <Tab
            label={
              <Box display="flex" alignItems="center" gap={1}>
                Active Syncs
                {statusCounts.in_progress > 0 && (
                  <Chip label={statusCounts.in_progress} size="small" color="primary" />
                )}
              </Box>
            }
          />
          <Tab
            label={
              <Box display="flex" alignItems="center" gap={1}>
                Recent
                {completedSyncs.length > 0 && (
                  <Chip label={completedSyncs.length} size="small" color="default" />
                )}
              </Box>
            }
          />
        </Tabs>
      </Box>

      {/* Sync Lists */}
      <Box>
        {activeTab === 0 && (
          <>
            {inProgressSyncs.length === 0 ? (
              <Card>
                <CardContent sx={{ textAlign: 'center', py: 4 }}>
                  <TimelineIcon sx={{ fontSize: 48, color: 'text.disabled', mb: 2 }} />
                  <Typography variant="h6" gutterBottom>
                    No Active Syncs
                  </Typography>
                  <Typography variant="body2" color="text.secondary" paragraph>
                    There are no sync operations currently running.
                    {stats?.total_cc_pairs === 0
                      ? ' Start by setting up your first connector and destination.'
                      : ' Start a sync from your configured CC-Pairs.'}
                  </Typography>
                  <Stack direction="row" spacing={2} justifyContent="center" sx={{ mt: 2 }}>
                    <Button
                      variant="contained"
                      color="primary"
                      onClick={() => navigate('/destinations')}
                      startIcon={<SendIcon />}
                    >
                      Setup Destinations
                    </Button>
                    <Button
                      variant="outlined"
                      onClick={() => navigate('/connectors')}
                      startIcon={<CableIcon />}
                    >
                      Configure Connectors
                    </Button>
                  </Stack>
                </CardContent>
              </Card>
            ) : (
              <Stack spacing={2}>
                {inProgressSyncs.map((sync) => (
                  <SyncProgressCard key={sync.id} attempt={sync} showCancelButton={true} />
                ))}
              </Stack>
            )}
          </>
        )}

        {activeTab === 1 && (
          <>
            {completedSyncs.length === 0 ? (
              <Card>
                <CardContent>
                  <Typography variant="body1" color="text.secondary" textAlign="center">
                    No recent completed syncs
                  </Typography>
                </CardContent>
              </Card>
            ) : (
              <Stack spacing={2}>
                {completedSyncs.slice(0, 20).map((sync) => (
                  <SyncProgressCard
                    key={sync.id}
                    attempt={sync}
                    showCancelButton={false}
                    compact={true}
                  />
                ))}
              </Stack>
            )}
          </>
        )}
      </Box>

      {/* Auto-refresh indicator */}
      <Box
        position="fixed"
        bottom={20}
        right={20}
        sx={{
          backgroundColor: theme.palette.primary.main,
          color: 'white',
          p: 1,
          borderRadius: 1,
          fontSize: '0.75rem',
          opacity: 0.8,
        }}
      >
        Auto-refreshing every 5s
      </Box>
    </Box>
  );
};

export default SyncMonitoringPage;
