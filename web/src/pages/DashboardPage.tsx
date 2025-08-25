/**
 * DashboardPage - Onboarding and overview dashboard
 * Provides guidance on getting started and system overview
 */

import {
  ArrowForward as ArrowIcon,
  Cable as CableIcon,
  CheckCircle as CheckIcon,
  Person as PersonIcon,
  PlayArrow as PlayIcon,
  Security as SecurityIcon,
  Send as SendIcon,
  Speed as SpeedIcon,
  Storage as StorageIcon,
  Timeline as TimelineIcon,
} from '@mui/icons-material';
import {
  Alert,
  Avatar,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Divider,
  Grid,
  LinearProgress,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Stack,
  Step,
  StepContent,
  StepLabel,
  Stepper,
  Typography,
} from '@mui/material';
import { useQuery } from '@tanstack/react-query';
import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useActiveSyncs } from '../hooks/useActiveSyncs';
import { api } from '../lib/api';

interface DashboardStats {
  total_destinations: number;
  total_connectors: number;
  total_profiles: number;
  total_cc_pairs: number;
  active_syncs: number;
  recent_sync_success_rate: number;
}

const DashboardPage: React.FC = () => {
  const navigate = useNavigate();

  // Fetch dashboard statistics
  const { data: stats, isLoading: statsLoading } = useQuery<DashboardStats>({
    queryKey: ['dashboard-stats'],
    queryFn: async () => {
      // We'll need to make multiple API calls since there's no single stats endpoint
      const [destinations, profiles, ccPairs] = await Promise.all([
        api.get('/targets/'),
        api.get('/profiles/'),
        api.get('/cc-pairs/'),
      ]);

      return {
        total_destinations: destinations.data?.length || 0,
        total_connectors: 0, // We'll calculate this from profiles
        total_profiles: profiles.data?.length || 0,
        total_cc_pairs: ccPairs.data?.length || 0,
        active_syncs: 0,
        recent_sync_success_rate: 95, // Placeholder
      };
    },
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
  });

  const { data: activeSyncs } = useActiveSyncs();
  const activeCount = activeSyncs?.filter((sync) => sync.status === 'IN_PROGRESS').length || 0;

  const getSetupProgress = () => {
    if (!stats) return { completed: 0, total: 4 };

    let completed = 0;
    const total = 4;

    if (stats.total_destinations > 0) completed++;
    if (stats.total_profiles > 0) completed++;
    if (stats.total_cc_pairs > 0) completed++;
    if (stats.active_syncs > 0 || activeCount > 0) completed++;

    return { completed, total };
  };

  const setupProgress = getSetupProgress();
  const progressPercentage = (setupProgress.completed / setupProgress.total) * 100;

  const setupSteps = [
    {
      label: 'Set Up Destinations',
      description: 'Configure where your data will be sent (e.g., CleverBrag, CSV)',
      completed: (stats?.total_destinations || 0) > 0,
      action: () => navigate('/destinations'),
      actionLabel: 'Configure Destinations',
      icon: <SendIcon />,
      color: 'primary' as const,
    },
    {
      label: 'Create Credentials',
      description: 'Set up authentication for your data sources',
      completed: (stats?.total_profiles || 0) > 0,
      action: () => navigate('/profiles'),
      actionLabel: 'Add Credentials',
      icon: <PersonIcon />,
      color: 'warning' as const,
    },
    {
      label: 'Connect Data Sources',
      description: 'Link connectors with credentials to create sync pairs',
      completed: (stats?.total_cc_pairs || 0) > 0,
      action: () => navigate('/connectors'),
      actionLabel: 'Setup Connectors',
      icon: <CableIcon />,
      color: 'info' as const,
    },
    {
      label: 'Start Syncing',
      description: 'Monitor your data syncs in real-time',
      completed: activeCount > 0,
      action: () => navigate('/sync-monitoring'),
      actionLabel: 'View Sync Monitor',
      icon: <PlayIcon />,
      color: 'success' as const,
    },
  ];

  if (statsLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <LinearProgress sx={{ width: '50%' }} />
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      {/* Welcome Header */}
      <Box mb={4}>
        <Typography variant="h3" gutterBottom>
          Welcome to Integration Server
        </Typography>
        <Typography variant="h6" color="text.secondary" gutterBottom>
          Connect 80+ data sources to multiple destinations with enterprise-grade security
        </Typography>

        {/* Setup Progress */}
        <Card sx={{ mt: 2, bgcolor: 'primary.main', color: 'white' }}>
          <CardContent>
            <Box display="flex" alignItems="center" justifyContent="space-between">
              <Box>
                <Typography variant="h6" sx={{ color: 'white' }}>
                  Setup Progress: {setupProgress.completed} of {setupProgress.total} completed
                </Typography>
                <LinearProgress
                  variant="determinate"
                  value={progressPercentage}
                  sx={{ mt: 1, bgcolor: 'rgba(255,255,255,0.3)' }}
                />
              </Box>
              <Avatar sx={{ bgcolor: 'rgba(255,255,255,0.2)' }}>
                <CheckIcon />
              </Avatar>
            </Box>
          </CardContent>
        </Card>
      </Box>

      {/* Quick Stats */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography variant="h4" color="primary">
                    {stats?.total_destinations || 0}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Destinations
                  </Typography>
                </Box>
                <SendIcon color="primary" fontSize="large" />
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
                    {stats?.total_profiles || 0}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Credentials
                  </Typography>
                </Box>
                <SecurityIcon color="warning" fontSize="large" />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography variant="h4" color="info.main">
                    {stats?.total_cc_pairs || 0}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Sync Pairs
                  </Typography>
                </Box>
                <StorageIcon color="info" fontSize="large" />
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
                    {activeCount}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Active Syncs
                  </Typography>
                </Box>
                <SpeedIcon color="success" fontSize="large" />
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Grid container spacing={3}>
        {/* Getting Started Guide */}
        <Grid item xs={12} lg={8}>
          <Card>
            <CardContent>
              <Typography variant="h5" gutterBottom>
                Getting Started
              </Typography>
              <Typography variant="body2" color="text.secondary" paragraph>
                Follow these steps to set up your first data sync
              </Typography>

              <Stepper orientation="vertical">
                {setupSteps.map((step) => (
                  <Step key={step.label} active={true}>
                    <StepLabel
                      icon={
                        <Avatar
                          sx={{
                            bgcolor: step.completed ? 'success.main' : `${step.color}.main`,
                            width: 32,
                            height: 32,
                          }}
                        >
                          {step.completed ? <CheckIcon /> : step.icon}
                        </Avatar>
                      }
                    >
                      <Box display="flex" alignItems="center" gap={1}>
                        <Typography variant="h6">{step.label}</Typography>
                        {step.completed && <Chip label="Complete" color="success" size="small" />}
                      </Box>
                    </StepLabel>
                    <StepContent>
                      <Typography variant="body2" color="text.secondary" paragraph>
                        {step.description}
                      </Typography>
                      {!step.completed && (
                        <Button
                          variant="contained"
                          color={step.color}
                          onClick={step.action}
                          endIcon={<ArrowIcon />}
                          sx={{ mb: 2 }}
                        >
                          {step.actionLabel}
                        </Button>
                      )}
                    </StepContent>
                  </Step>
                ))}
              </Stepper>
            </CardContent>
          </Card>
        </Grid>

        {/* Quick Actions & Tips */}
        <Grid item xs={12} lg={4}>
          <Stack spacing={3}>
            {/* Quick Actions */}
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Quick Actions
                </Typography>
                <List dense>
                  <ListItem>
                    <ListItemIcon>
                      <SendIcon color="primary" />
                    </ListItemIcon>
                    <ListItemText primary="View API Docs" secondary="Comprehensive API reference" />
                    <Button
                      size="small"
                      onClick={() => window.open('http://localhost:8000/docs', '_blank')}
                    >
                      Open
                    </Button>
                  </ListItem>
                  <Divider />
                  <ListItem>
                    <ListItemIcon>
                      <TimelineIcon color="success" />
                    </ListItemIcon>
                    <ListItemText primary="System Health" secondary="Check system status" />
                    <Button
                      size="small"
                      onClick={() => window.open('http://localhost:8000/health', '_blank')}
                    >
                      Check
                    </Button>
                  </ListItem>
                </List>
              </CardContent>
            </Card>

            {/* Tips */}
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  💡 Tips
                </Typography>
                <List dense>
                  <ListItem>
                    <ListItemText
                      primary="Start with CleverBrag"
                      secondary="Most users begin with a CleverBrag destination"
                    />
                  </ListItem>
                  <ListItem>
                    <ListItemText
                      primary="Google OAuth Setup"
                      secondary="Set up Google OAuth for Gmail and Drive connectors"
                    />
                  </ListItem>
                  <ListItem>
                    <ListItemText
                      primary="Monitor Progress"
                      secondary="Use the Sync Monitor to track real-time progress"
                    />
                  </ListItem>
                </List>
              </CardContent>
            </Card>

            {/* Status */}
            {progressPercentage === 100 && (
              <Alert severity="success">
                🎉 Setup complete! Your integration server is ready for production use.
              </Alert>
            )}
          </Stack>
        </Grid>
      </Grid>
    </Box>
  );
};

export default DashboardPage;
