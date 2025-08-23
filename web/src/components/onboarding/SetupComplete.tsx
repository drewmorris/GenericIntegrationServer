/**
 * Setup Complete Component
 * Celebrates successful destination setup and guides next steps
 * Follows Material Design success patterns with clear call-to-action
 */

import {
  Add as AddIcon,
  CheckCircle as CheckCircleIcon,
  PlayArrow as PlayArrowIcon,
  Security as SecurityIcon,
  Settings as SettingsIcon,
  Speed as SpeedIcon,
  TrendingUp as TrendingUpIcon,
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
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Typography,
} from '@mui/material';
import type React from 'react';
import { useId } from 'react';

import { getDestinationLogo } from '../../assets/connector-logos';

type SetupCompleteProps = {
  wizardData: Record<string, any>;
  onDataChange: (data: any) => void;
};

export const SetupComplete: React.FC<SetupCompleteProps> = ({ wizardData }) => {
  // Generate unique ID
  const setupCompleteHeadingId = useId();

  const destinationType = wizardData.destinationType;
  const destinationMeta = wizardData.destinationMetadata;
  const testResults = wizardData.testResults || [];
  const testStatus = wizardData.testStatus || 'success';

  const successfulTests = testResults.filter((r: any) => r.status === 'success').length;
  const totalTests = testResults.length;

  const nextSteps = [
    {
      icon: AddIcon,
      title: 'Add Your First Connector',
      description: 'Connect data sources like Gmail, Slack, or databases to start syncing',
      action: 'Add Connector',
      primary: true,
    },
    {
      icon: SettingsIcon,
      title: 'Configure Sync Settings',
      description: 'Set up sync schedules, filters, and data transformation rules',
      action: 'Configure',
    },
    {
      icon: TrendingUpIcon,
      title: 'Monitor Performance',
      description: 'Track sync status, data flow, and system performance',
      action: 'View Dashboard',
    },
  ];

  const features = [
    {
      icon: SecurityIcon,
      title: 'Secure Connection',
      description: 'Your data is encrypted in transit and at rest',
    },
    {
      icon: SpeedIcon,
      title: 'High Performance',
      description: 'Optimized for fast, reliable data synchronization',
    },
    {
      icon: CheckCircleIcon,
      title: 'Tested & Verified',
      description: 'Connection successfully tested and ready to use',
    },
  ];

  return (
    <Box role="region" aria-labelledby="setup-complete-heading">
      {/* Success Header */}
      <Box textAlign="center" sx={{ mb: 4 }}>
        <CheckCircleIcon
          sx={{
            fontSize: 80,
            color: 'success.main',
            mb: 2,
          }}
          aria-hidden="true"
        />

        <Typography
          id={setupCompleteHeadingId}
          variant="h4"
          component="h1"
          gutterBottom
          sx={{ fontWeight: 300 }}
        >
          🎉 Destination Setup Complete!
        </Typography>

        <Typography variant="h6" color="text.secondary" sx={{ mb: 3 }}>
          Your {destinationMeta?.displayName || destinationType} destination is ready to receive
          data
        </Typography>

        {/* Test Results Summary */}
        <Alert
          severity={testStatus === 'error' ? 'warning' : 'success'}
          sx={{ mb: 3, textAlign: 'left' }}
          role="status"
        >
          <Typography variant="body2">
            <strong>Connection Test Results:</strong> {successfulTests}/{totalTests} tests passed
            {testStatus === 'warning' && ' with warnings'}
            {testStatus === 'error' && ' - some issues detected but destination is functional'}
          </Typography>
        </Alert>
      </Box>

      {/* Destination Summary Card */}
      <Card elevation={2} sx={{ mb: 4 }}>
        <CardContent sx={{ p: 3 }}>
          <Box display="flex" alignItems="center" gap={3} mb={3}>
            <Avatar
              src={getDestinationLogo(destinationType)}
              alt={`${destinationMeta?.displayName} logo`}
              sx={{
                width: 64,
                height: 64,
                border: '3px solid',
                borderColor: 'success.main',
                bgcolor: 'background.paper',
              }}
            />
            <Box flex={1}>
              <Typography variant="h5" component="h2" gutterBottom>
                {destinationMeta?.displayName || destinationType}
              </Typography>
              <Typography variant="body1" color="text.secondary" sx={{ mb: 2 }}>
                {destinationMeta?.description}
              </Typography>
              <Box display="flex" gap={1} flexWrap="wrap">
                <Chip
                  label={`Difficulty: ${destinationMeta?.difficulty || 'Medium'}`}
                  size="small"
                  color={
                    destinationMeta?.difficulty === 'Easy'
                      ? 'success'
                      : destinationMeta?.difficulty === 'Advanced'
                        ? 'error'
                        : 'warning'
                  }
                  variant="outlined"
                />
                {destinationMeta?.enterprise && (
                  <Chip label="Enterprise" size="small" color="info" variant="outlined" />
                )}
                <Chip label="Connected" size="small" color="success" icon={<CheckCircleIcon />} />
              </Box>
            </Box>
          </Box>

          {/* Features */}
          <Divider sx={{ mb: 3 }} />
          <Typography variant="h6" gutterBottom>
            What You Get
          </Typography>
          <List dense>
            {features.map((feature) => (
              <ListItem key={feature.title} sx={{ px: 0 }}>
                <ListItemIcon>
                  <feature.icon color="success" />
                </ListItemIcon>
                <ListItemText primary={feature.title} secondary={feature.description} />
              </ListItem>
            ))}
          </List>
        </CardContent>
      </Card>

      {/* Next Steps */}
      <Typography variant="h5" component="h2" gutterBottom sx={{ mb: 3 }}>
        What's Next?
      </Typography>

      <Box sx={{ mb: 4 }}>
        {nextSteps.map((step) => (
          <Card
            key={step.title}
            elevation={step.primary ? 2 : 1}
            sx={{
              mb: 2,
              border: step.primary ? '2px solid' : '1px solid',
              borderColor: step.primary ? 'primary.main' : 'divider',
            }}
          >
            <CardContent sx={{ p: 3 }}>
              <Box display="flex" alignItems="center" gap={2}>
                <Avatar
                  sx={{
                    bgcolor: step.primary ? 'primary.main' : 'grey.100',
                    color: step.primary ? 'white' : 'grey.600',
                    width: 48,
                    height: 48,
                  }}
                >
                  <step.icon />
                </Avatar>
                <Box flex={1}>
                  <Typography variant="h6" component="h3" gutterBottom>
                    {step.title}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {step.description}
                  </Typography>
                </Box>
                <Button
                  variant={step.primary ? 'contained' : 'outlined'}
                  size="large"
                  startIcon={step.primary ? <PlayArrowIcon /> : undefined}
                  aria-label={`${step.action} - ${step.title}`}
                >
                  {step.action}
                </Button>
              </Box>
            </CardContent>
          </Card>
        ))}
      </Box>

      {/* Additional Resources */}
      <Card variant="outlined" sx={{ mb: 4 }}>
        <CardContent sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>
            Need Help Getting Started?
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Explore our resources to make the most of your integration setup.
          </Typography>

          <Box display="flex" gap={2} flexWrap="wrap">
            <Button
              variant="text"
              href="/docs/getting-started"
              target="_blank"
              rel="noopener noreferrer"
              size="small"
            >
              Getting Started Guide
            </Button>
            <Button
              variant="text"
              href="/docs/connectors"
              target="_blank"
              rel="noopener noreferrer"
              size="small"
            >
              Connector Documentation
            </Button>
            <Button
              variant="text"
              href="/docs/best-practices"
              target="_blank"
              rel="noopener noreferrer"
              size="small"
            >
              Best Practices
            </Button>
            <Button variant="text" href="/support" size="small">
              Contact Support
            </Button>
          </Box>
        </CardContent>
      </Card>

      {/* Success Message */}
      <Alert severity="success" sx={{ textAlign: 'center' }}>
        <Typography variant="body1">
          <strong>Congratulations!</strong> Your destination is configured and ready. You can now
          add connectors to start syncing your data.
        </Typography>
      </Alert>
    </Box>
  );
};
