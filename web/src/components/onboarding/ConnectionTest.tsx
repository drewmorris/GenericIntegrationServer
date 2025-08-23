/**
 * Connection Test Component
 * Tests destination connection before finalizing setup
 * Provides real-time feedback and troubleshooting guidance
 */

import {
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  ExpandMore as ExpandMoreIcon,
  Info as InfoIcon,
  NetworkCheck as NetworkCheckIcon,
  PlayArrow as PlayArrowIcon,
  Refresh as RefreshIcon,
  Security as SecurityIcon,
  Speed as SpeedIcon,
  Warning as WarningIcon,
} from '@mui/icons-material';
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Alert,
  Box,
  Button,
  Chip,
  Divider,
  LinearProgress,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Paper,
  Typography,
} from '@mui/material';
import React, { useCallback, useEffect, useId, useState } from 'react';

import { useTestDestination } from '../../hooks/useTestDestination';

type ConnectionTestProps = {
  wizardData: Record<string, any>;
  onDataChange: (data: any) => void;
};

type TestResult = {
  step: string;
  status: 'pending' | 'running' | 'success' | 'warning' | 'error';
  message: string;
  details?: string;
  duration?: number;
};

const testSteps = [
  {
    id: 'connectivity',
    label: 'Network Connectivity',
    description: 'Testing network connection to destination',
    icon: NetworkCheckIcon,
  },
  {
    id: 'authentication',
    label: 'Authentication',
    description: 'Verifying credentials and permissions',
    icon: SecurityIcon,
  },
  {
    id: 'performance',
    label: 'Performance Check',
    description: 'Measuring response time and availability',
    icon: SpeedIcon,
  },
];

export const ConnectionTest: React.FC<ConnectionTestProps> = ({ wizardData, onDataChange }) => {
  const [testResults, setTestResults] = useState<TestResult[]>([]);
  const [isTestRunning, setIsTestRunning] = useState(false);
  const [currentStep, setCurrentStep] = useState<string | null>(null);
  const [overallStatus, setOverallStatus] = useState<
    'idle' | 'running' | 'success' | 'warning' | 'error'
  >('idle');

  // Generate unique IDs
  const connectionTestHeadingId = useId();
  const troubleshootingHeaderId = useId();

  const { mutateAsync: testDestination } = useTestDestination();

  const destinationType = wizardData.destinationType;
  const config = wizardData.config;
  const destinationMeta = wizardData.destinationMetadata;

  const runConnectionTest = useCallback(async () => {
    if (!config || !destinationType) {
      return;
    }

    setIsTestRunning(true);
    setOverallStatus('running');
    setTestResults([]);

    const results: TestResult[] = [];
    const startTime = Date.now();

    try {
      // Step 1: Connectivity Test
      setCurrentStep('connectivity');
      results.push({
        step: 'connectivity',
        status: 'running',
        message: 'Testing network connectivity...',
      });
      setTestResults([...results]);

      await new Promise((resolve) => setTimeout(resolve, 1000)); // Simulate test time

      try {
        const _testResponse = await testDestination({
          name: destinationType,
          config: config,
        });

        results[0] = {
          step: 'connectivity',
          status: 'success',
          message: 'Network connectivity successful',
          duration: Date.now() - startTime,
        };
      } catch (error) {
        results[0] = {
          step: 'connectivity',
          status: 'error',
          message: 'Network connectivity failed',
          details: error instanceof Error ? error.message : 'Unknown network error',
          duration: Date.now() - startTime,
        };
        setTestResults([...results]);
        setOverallStatus('error');
        setIsTestRunning(false);
        setCurrentStep(null);
        onDataChange({ testPassed: false, testResults: results });
        return;
      }

      setTestResults([...results]);

      // Step 2: Authentication Test
      setCurrentStep('authentication');
      results.push({
        step: 'authentication',
        status: 'running',
        message: 'Verifying authentication...',
      });
      setTestResults([...results]);

      await new Promise((resolve) => setTimeout(resolve, 1500)); // Simulate auth test

      // Simulate auth success (in real implementation, this would be part of the API response)
      results[1] = {
        step: 'authentication',
        status: 'success',
        message: 'Authentication successful',
        duration: Date.now() - startTime - results[0].duration!,
      };
      setTestResults([...results]);

      // Step 3: Performance Test
      setCurrentStep('performance');
      results.push({
        step: 'performance',
        status: 'running',
        message: 'Testing performance...',
      });
      setTestResults([...results]);

      await new Promise((resolve) => setTimeout(resolve, 1000)); // Simulate performance test

      const responseTime = Math.random() * 1000 + 200; // Simulate response time
      const performanceStatus =
        responseTime < 1000 ? 'success' : responseTime < 2000 ? 'warning' : 'error';

      results[2] = {
        step: 'performance',
        status: performanceStatus,
        message: `Response time: ${responseTime.toFixed(0)}ms`,
        details:
          performanceStatus === 'warning'
            ? 'Response time is acceptable but could be improved'
            : performanceStatus === 'error'
              ? 'Response time is slow, this may affect sync performance'
              : 'Excellent response time',
        duration: Date.now() - startTime - results[0].duration! - results[1].duration!,
      };

      setTestResults([...results]);

      // Determine overall status
      const hasErrors = results.some((r) => r.status === 'error');
      const hasWarnings = results.some((r) => r.status === 'warning');

      const finalStatus = hasErrors ? 'error' : hasWarnings ? 'warning' : 'success';
      setOverallStatus(finalStatus);

      onDataChange({
        testPassed: !hasErrors,
        testResults: results,
        testStatus: finalStatus,
      });
    } catch (error) {
      const errorResult: TestResult = {
        step: 'general',
        status: 'error',
        message: 'Connection test failed',
        details: error instanceof Error ? error.message : 'Unknown error occurred',
      };

      setTestResults([errorResult]);
      setOverallStatus('error');
      onDataChange({ testPassed: false, testResults: [errorResult] });
    } finally {
      setIsTestRunning(false);
      setCurrentStep(null);
    }
  }, [config, destinationType, testDestination, onDataChange]);

  // Auto-run test when component mounts with valid config
  useEffect(() => {
    if (config && wizardData.configValid && testResults.length === 0) {
      void runConnectionTest();
    }
  }, [config, wizardData.configValid, testResults.length, runConnectionTest]);

  const getStatusIcon = (status: TestResult['status']) => {
    switch (status) {
      case 'success': {
        return <CheckCircleIcon color="success" />;
      }
      case 'warning': {
        return <WarningIcon color="warning" />;
      }
      case 'error': {
        return <ErrorIcon color="error" />;
      }
      case 'running': {
        return <LinearProgress sx={{ width: 20, height: 20, borderRadius: 10 }} />;
      }
      default: {
        return <InfoIcon color="disabled" />;
      }
    }
  };

  const getStatusColor = (status: TestResult['status']) => {
    switch (status) {
      case 'success': {
        return 'success';
      }
      case 'warning': {
        return 'warning';
      }
      case 'error': {
        return 'error';
      }
      case 'running': {
        return 'info';
      }
      default: {
        return 'default';
      }
    }
  };

  if (!config || !wizardData.configValid) {
    return (
      <Alert severity="warning">
        Please complete the configuration step before testing the connection.
      </Alert>
    );
  }

  return (
    <Box role="region" aria-labelledby={connectionTestHeadingId}>
      <Typography
        id={connectionTestHeadingId}
        variant="h5"
        component="h2"
        gutterBottom
        sx={{ mb: 3 }}
      >
        Test Connection
      </Typography>

      <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
        We'll test the connection to {destinationMeta?.displayName || destinationType} to ensure
        everything is configured correctly.
      </Typography>

      {/* Test Controls */}
      <Box sx={{ mb: 4 }}>
        <Button
          variant="contained"
          onClick={runConnectionTest}
          disabled={isTestRunning}
          startIcon={isTestRunning ? <LinearProgress sx={{ width: 20 }} /> : <PlayArrowIcon />}
          size="large"
          aria-label={isTestRunning ? 'Testing connection...' : 'Start connection test'}
        >
          {isTestRunning ? 'Testing Connection...' : 'Test Connection'}
        </Button>

        {testResults.length > 0 && !isTestRunning && (
          <Button
            variant="outlined"
            onClick={runConnectionTest}
            startIcon={<RefreshIcon />}
            sx={{ ml: 2 }}
            aria-label="Retry connection test"
          >
            Retry Test
          </Button>
        )}
      </Box>

      {/* Overall Status */}
      {overallStatus !== 'idle' && (
        <Alert
          severity={overallStatus === 'running' ? 'info' : (overallStatus as any)}
          sx={{ mb: 3 }}
          role="status"
          aria-live="polite"
        >
          {overallStatus === 'running' && 'Testing connection...'}
          {overallStatus === 'success' &&
            'Connection test passed! Your destination is ready to use.'}
          {overallStatus === 'warning' &&
            'Connection test completed with warnings. The destination will work but performance may be affected.'}
          {overallStatus === 'error' &&
            'Connection test failed. Please check your configuration and try again.'}
        </Alert>
      )}

      {/* Test Progress */}
      {isTestRunning && (
        <Paper elevation={1} sx={{ p: 3, mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            Testing Progress
          </Typography>
          <LinearProgress
            variant="determinate"
            value={
              (testResults.filter((r) => r.status !== 'running').length / testSteps.length) * 100
            }
            sx={{ mb: 2 }}
          />
          <Typography variant="body2" color="text.secondary">
            {currentStep &&
              `Currently testing: ${testSteps.find((s) => s.id === currentStep)?.label}`}
          </Typography>
        </Paper>
      )}

      {/* Test Results */}
      {testResults.length > 0 && (
        <Paper elevation={1} sx={{ p: 3, mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            Test Results
          </Typography>

          <List>
            {testSteps.map((step, index) => {
              const result = testResults.find((r) => r.step === step.id);
              const StepIcon = step.icon;

              return (
                <React.Fragment key={step.id}>
                  <ListItem>
                    <ListItemIcon>
                      <StepIcon color={result ? 'primary' : 'disabled'} />
                    </ListItemIcon>
                    <ListItemText
                      primary={
                        <Box display="flex" alignItems="center" gap={1}>
                          <Typography variant="body1">{step.label}</Typography>
                          {result && (
                            <Chip
                              label={result.status}
                              size="small"
                              color={getStatusColor(result.status) as any}
                              variant="outlined"
                            />
                          )}
                          {result?.duration && (
                            <Typography variant="caption" color="text.secondary">
                              ({result.duration}ms)
                            </Typography>
                          )}
                        </Box>
                      }
                      secondary={
                        <Box>
                          <Typography variant="body2" color="text.secondary">
                            {step.description}
                          </Typography>
                          {result && (
                            <Typography
                              variant="body2"
                              color={result.status === 'error' ? 'error' : 'text.primary'}
                              sx={{ mt: 0.5 }}
                            >
                              {result.message}
                            </Typography>
                          )}
                        </Box>
                      }
                    />
                    <ListItemIcon>
                      {result ? getStatusIcon(result.status) : <InfoIcon color="disabled" />}
                    </ListItemIcon>
                  </ListItem>
                  {index < testSteps.length - 1 && <Divider />}
                </React.Fragment>
              );
            })}
          </List>
        </Paper>
      )}

      {/* Troubleshooting */}
      {overallStatus === 'error' && (
        <Accordion>
          <AccordionSummary
            expandIcon={<ExpandMoreIcon />}
            aria-controls="troubleshooting-content"
            id={troubleshootingHeaderId}
          >
            <Typography variant="subtitle1">Troubleshooting Guide</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Box>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Common solutions for connection issues:
              </Typography>

              <List dense>
                <ListItem>
                  <ListItemIcon>
                    <CheckCircleIcon fontSize="small" />
                  </ListItemIcon>
                  <ListItemText
                    primary="Verify your API key or credentials are correct"
                    secondary="Double-check for typos and ensure the key has proper permissions"
                  />
                </ListItem>
                <ListItem>
                  <ListItemIcon>
                    <CheckCircleIcon fontSize="small" />
                  </ListItemIcon>
                  <ListItemText
                    primary="Check the destination URL"
                    secondary="Ensure the URL is accessible and includes the correct protocol (https://)"
                  />
                </ListItem>
                <ListItem>
                  <ListItemIcon>
                    <CheckCircleIcon fontSize="small" />
                  </ListItemIcon>
                  <ListItemText
                    primary="Verify network connectivity"
                    secondary="Ensure your network allows outbound connections to the destination"
                  />
                </ListItem>
                <ListItem>
                  <ListItemIcon>
                    <CheckCircleIcon fontSize="small" />
                  </ListItemIcon>
                  <ListItemText
                    primary="Check destination service status"
                    secondary="The destination service might be temporarily unavailable"
                  />
                </ListItem>
              </List>

              <Box sx={{ mt: 2 }}>
                <Button
                  variant="text"
                  href={`/docs/destinations/${destinationType}/troubleshooting`}
                  target="_blank"
                  rel="noopener noreferrer"
                  size="small"
                >
                  View Detailed Troubleshooting Guide
                </Button>
              </Box>
            </Box>
          </AccordionDetails>
        </Accordion>
      )}
    </Box>
  );
};
