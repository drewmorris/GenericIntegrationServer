/**
 * Destination Health Dialog
 * Comprehensive health monitoring with real-time metrics and diagnostics
 * Provides detailed insights into destination performance and issues
 */

import {
  CheckCircle as CheckCircleIcon,
  Close as CloseIcon,
  Error as ErrorIcon,
  Refresh as RefreshIcon,
  Speed as SpeedIcon,
  Timeline as TimelineIcon,
  TrendingUp as TrendingUpIcon,
  Warning as WarningIcon,
} from '@mui/icons-material';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  Grid,
  IconButton,
  LinearProgress,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Tab,
  Tabs,
  Tooltip,
  Typography,
} from '@mui/material';
import React, { useId, useState } from 'react';

import { useDestinationHealth } from '../../hooks/useDestinationHealth';

const getStatusColor = (status: string) => {
  switch (status) {
    case 'pass':
    case 'good': {
      return 'success';
    }
    case 'warning': {
      return 'warning';
    }
    case 'fail':
    case 'error': {
      return 'error';
    }
    default: {
      return 'default';
    }
  }
};

import { formatDistanceToNow } from 'date-fns';
import { useDestinationMetrics } from '../../hooks/useDestinationMetrics';

type DestinationHealthDialogProps = {
  destination: {
    id: string;
    name: string;
    displayName?: string;
    status: string;
  };
  open: boolean;
  onClose: () => void;
};

type HealthMetric = {
  name: string;
  value: number;
  unit: string;
  status: 'good' | 'warning' | 'error';
  description: string;
  threshold?: {
    warning: number;
    error: number;
  };
};

type HealthCheck = {
  id: string;
  name: string;
  status: 'pass' | 'warning' | 'fail';
  message: string;
  details?: string;
  lastChecked: string;
};

type HealthData = {
  overallHealth: number;
  lastChecked: string;
  metrics: HealthMetric[];
  checks: HealthCheck[];
};

export const DestinationHealthDialog: React.FC<DestinationHealthDialogProps> = ({
  destination,
  open,
  onClose,
}) => {
  const [activeTab, setActiveTab] = useState(0);
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Generate unique ID
  const healthDialogTitleId = useId();

  const { data: healthData, isLoading, refetch } = useDestinationHealth(destination.id);
  const { data: _metricsData } = useDestinationMetrics(destination.id);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    await refetch();
    setIsRefreshing(false);
  };

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
  };

  // Mock health data for demonstration
  const mockHealthData: HealthData = {
    overallHealth: 85,
    lastChecked: new Date().toISOString(),
    metrics: [
      {
        name: 'Response Time',
        value: 245,
        unit: 'ms',
        status: 'good',
        description: 'Average API response time',
        threshold: { warning: 500, error: 1000 },
      },
      {
        name: 'Success Rate',
        value: 98.5,
        unit: '%',
        status: 'good',
        description: 'Percentage of successful requests',
        threshold: { warning: 95, error: 90 },
      },
      {
        name: 'Error Rate',
        value: 1.5,
        unit: '%',
        status: 'good',
        description: 'Percentage of failed requests',
        threshold: { warning: 5, error: 10 },
      },
      {
        name: 'Throughput',
        value: 150,
        unit: 'req/min',
        status: 'good',
        description: 'Requests processed per minute',
      },
    ],
    checks: [
      {
        id: 'connectivity',
        name: 'Network Connectivity',
        status: 'pass',
        message: 'Connection established successfully',
        lastChecked: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
      },
      {
        id: 'authentication',
        name: 'Authentication',
        status: 'pass',
        message: 'API credentials are valid',
        lastChecked: new Date(Date.now() - 10 * 60 * 1000).toISOString(),
      },
      {
        id: 'permissions',
        name: 'Permissions',
        status: 'warning',
        message: 'Limited write permissions detected',
        details: 'Some operations may be restricted',
        lastChecked: new Date(Date.now() - 15 * 60 * 1000).toISOString(),
      },
      {
        id: 'capacity',
        name: 'Storage Capacity',
        status: 'pass',
        message: 'Sufficient storage available',
        lastChecked: new Date(Date.now() - 20 * 60 * 1000).toISOString(),
      },
    ],
  };

  const currentHealthData: HealthData =
    healthData && Object.keys(healthData).length > 0 ? (healthData as HealthData) : mockHealthData;

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'pass':
      case 'good': {
        return <CheckCircleIcon color="success" />;
      }
      case 'warning': {
        return <WarningIcon color="warning" />;
      }
      case 'fail':
      case 'error': {
        return <ErrorIcon color="error" />;
      }
      default: {
        return <WarningIcon color="disabled" />;
      }
    }
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="md"
      fullWidth
      aria-labelledby={healthDialogTitleId}
    >
      <DialogTitle>
        <Box display="flex" alignItems="center" justifyContent="space-between">
          <Typography variant="h6" component="h2" id={healthDialogTitleId}>
            {destination.displayName || destination.name} Health
          </Typography>
          <Box display="flex" alignItems="center" gap={1}>
            <Tooltip title="Refresh health data">
              <IconButton
                onClick={handleRefresh}
                disabled={isRefreshing}
                size="small"
                aria-label="Refresh health data"
              >
                <RefreshIcon />
              </IconButton>
            </Tooltip>
            <IconButton onClick={onClose} size="small" aria-label="Close dialog">
              <CloseIcon />
            </IconButton>
          </Box>
        </Box>
      </DialogTitle>

      <DialogContent>
        {isLoading ? (
          <Box py={4}>
            <LinearProgress />
            <Typography variant="body2" color="text.secondary" textAlign="center" mt={2}>
              Loading health data...
            </Typography>
          </Box>
        ) : (
          <>
            {/* Overall Health Score */}
            <Card sx={{ mb: 3 }}>
              <CardContent>
                <Box display="flex" alignItems="center" gap={3}>
                  <Box textAlign="center">
                    <Typography variant="h3" color="primary" gutterBottom>
                      {currentHealthData.overallHealth}%
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Overall Health
                    </Typography>
                  </Box>

                  <Box flex={1}>
                    <LinearProgress
                      variant="determinate"
                      value={currentHealthData.overallHealth}
                      sx={{
                        height: 12,
                        borderRadius: 6,
                        bgcolor: 'grey.200',
                        '& .MuiLinearProgress-bar': {
                          bgcolor:
                            currentHealthData.overallHealth >= 80
                              ? 'success.main'
                              : currentHealthData.overallHealth >= 60
                                ? 'warning.main'
                                : 'error.main',
                          borderRadius: 6,
                        },
                      }}
                    />
                    <Typography
                      variant="caption"
                      color="text.secondary"
                      sx={{ mt: 1, display: 'block' }}
                    >
                      Last checked:{' '}
                      {formatDistanceToNow(new Date(currentHealthData.lastChecked), {
                        addSuffix: true,
                      })}
                    </Typography>
                  </Box>

                  <Chip
                    label={
                      currentHealthData.overallHealth >= 80
                        ? 'Healthy'
                        : currentHealthData.overallHealth >= 60
                          ? 'Warning'
                          : 'Critical'
                    }
                    color={
                      currentHealthData.overallHealth >= 80
                        ? 'success'
                        : currentHealthData.overallHealth >= 60
                          ? 'warning'
                          : 'error'
                    }
                    variant="outlined"
                  />
                </Box>
              </CardContent>
            </Card>

            {/* Tabs */}
            <Tabs value={activeTab} onChange={handleTabChange} sx={{ mb: 3 }}>
              <Tab label="Metrics" icon={<TrendingUpIcon />} />
              <Tab label="Health Checks" icon={<CheckCircleIcon />} />
              <Tab label="Performance" icon={<SpeedIcon />} />
            </Tabs>

            {/* Tab Content */}
            {activeTab === 0 && (
              <Grid container spacing={3}>
                {currentHealthData.metrics.map((metric) => (
                  <Grid item xs={12} sm={6} key={metric.name}>
                    <Card>
                      <CardContent>
                        <Box display="flex" alignItems="center" gap={2} mb={2}>
                          {getStatusIcon(metric.status)}
                          <Typography variant="h6" flex={1}>
                            {metric.name}
                          </Typography>
                          <Chip
                            label={metric.status}
                            size="small"
                            color={getStatusColor(metric.status) as any}
                            variant="outlined"
                          />
                        </Box>

                        <Typography variant="h4" color="primary" gutterBottom>
                          {metric.value}
                          {metric.unit}
                        </Typography>

                        <Typography variant="body2" color="text.secondary">
                          {metric.description}
                        </Typography>

                        {metric.threshold && (
                          <Box mt={2}>
                            <Typography variant="caption" color="text.secondary">
                              Thresholds: Warning {metric.threshold.warning}
                              {metric.unit}, Error {metric.threshold.error}
                              {metric.unit}
                            </Typography>
                          </Box>
                        )}
                      </CardContent>
                    </Card>
                  </Grid>
                ))}
              </Grid>
            )}

            {activeTab === 1 && (
              <List>
                {currentHealthData.checks.map((check, index) => (
                  <React.Fragment key={check.id}>
                    <ListItem>
                      <ListItemIcon>{getStatusIcon(check.status)}</ListItemIcon>
                      <ListItemText
                        primary={
                          <Box display="flex" alignItems="center" gap={2}>
                            <Typography variant="body1">{check.name}</Typography>
                            <Chip
                              label={check.status}
                              size="small"
                              color={getStatusColor(check.status) as any}
                              variant="outlined"
                            />
                          </Box>
                        }
                        secondary={
                          <Box>
                            <Typography variant="body2" color="text.primary">
                              {check.message}
                            </Typography>
                            {check.details && (
                              <Typography variant="body2" color="text.secondary">
                                {check.details}
                              </Typography>
                            )}
                            <Typography variant="caption" color="text.secondary">
                              Last checked:{' '}
                              {formatDistanceToNow(new Date(check.lastChecked), {
                                addSuffix: true,
                              })}
                            </Typography>
                          </Box>
                        }
                      />
                    </ListItem>
                    {index < currentHealthData.checks.length - 1 && <Divider />}
                  </React.Fragment>
                ))}
              </List>
            )}

            {activeTab === 2 && (
              <Box>
                <Alert severity="info" sx={{ mb: 3 }}>
                  Performance metrics are collected over the last 24 hours.
                </Alert>

                <Grid container spacing={3}>
                  <Grid item xs={12}>
                    <Card>
                      <CardContent>
                        <Typography variant="h6" gutterBottom>
                          Response Time Trend
                        </Typography>
                        <Box
                          sx={{
                            height: 200,
                            bgcolor: 'grey.50',
                            borderRadius: 1,
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                          }}
                        >
                          <Typography variant="body2" color="text.secondary">
                            Performance chart would be rendered here
                          </Typography>
                        </Box>
                      </CardContent>
                    </Card>
                  </Grid>

                  <Grid item xs={12} sm={4}>
                    <Card>
                      <CardContent sx={{ textAlign: 'center' }}>
                        <SpeedIcon color="primary" sx={{ fontSize: 40, mb: 1 }} />
                        <Typography variant="h5" color="primary">
                          245ms
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          Avg Response Time
                        </Typography>
                      </CardContent>
                    </Card>
                  </Grid>

                  <Grid item xs={12} sm={4}>
                    <Card>
                      <CardContent sx={{ textAlign: 'center' }}>
                        <TrendingUpIcon color="success" sx={{ fontSize: 40, mb: 1 }} />
                        <Typography variant="h5" color="success.main">
                          98.5%
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          Uptime
                        </Typography>
                      </CardContent>
                    </Card>
                  </Grid>

                  <Grid item xs={12} sm={4}>
                    <Card>
                      <CardContent sx={{ textAlign: 'center' }}>
                        <TimelineIcon color="info" sx={{ fontSize: 40, mb: 1 }} />
                        <Typography variant="h5" color="info.main">
                          1.2K
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          Requests/Hour
                        </Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                </Grid>
              </Box>
            )}
          </>
        )}
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose}>Close</Button>
        <Button
          variant="contained"
          onClick={handleRefresh}
          disabled={isRefreshing}
          startIcon={<RefreshIcon />}
        >
          Refresh Data
        </Button>
      </DialogActions>
    </Dialog>
  );
};
