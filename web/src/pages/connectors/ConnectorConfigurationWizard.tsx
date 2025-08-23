/**
 * Connector Configuration Wizard
 * Multi-step wizard for setting up connector-destination pairs
 * Supports OAuth flows, static credentials, and advanced configuration
 */

import {
  ArrowBack as ArrowBackIcon,
  ArrowForward as ArrowForwardIcon,
  CheckCircle as CheckCircleIcon,
  Security as SecurityIcon,
  Settings as SettingsIcon,
  Sync as SyncIcon,
} from '@mui/icons-material';
import {
  Alert,
  Avatar,
  Box,
  Button,
  Chip,
  Container,
  Fade,
  LinearProgress,
  Paper,
  Step,
  StepContent,
  StepLabel,
  Stepper,
  Typography,
} from '@mui/material';
import type React from 'react';
import { useCallback, useEffect, useId, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { getConnectorLogo, getDestinationLogo } from '../../assets/connector-logos';
import { AuthenticationStep } from '../../components/connectors/AuthenticationStep';
import { ConnectionTestStep } from '../../components/connectors/ConnectionTestStep';
import { ConnectorDetailsStep } from '../../components/connectors/ConnectorDetailsStep';
import { ConnectorSetupComplete } from '../../components/connectors/ConnectorSetupComplete';
import { SyncSettingsStep } from '../../components/connectors/SyncSettingsStep';
import { useCreateConnectorCredentialPair } from '../../hooks/useCreateConnectorCredentialPair';

type WizardStep = {
  id: string;
  label: string;
  description: string;
  icon: React.ComponentType;
  component: React.ComponentType<any>;
  optional?: boolean;
};

const steps: WizardStep[] = [
  {
    id: 'details',
    label: 'Connector Details',
    description: 'Configure basic connector information',
    icon: SettingsIcon,
    component: ConnectorDetailsStep,
  },
  {
    id: 'auth',
    label: 'Authentication',
    description: 'Set up authentication credentials',
    icon: SecurityIcon,
    component: AuthenticationStep,
  },
  {
    id: 'sync',
    label: 'Sync Settings',
    description: 'Configure synchronization preferences',
    icon: SyncIcon,
    component: SyncSettingsStep,
  },
  {
    id: 'test',
    label: 'Test Connection',
    description: 'Verify the connector configuration',
    icon: CheckCircleIcon,
    component: ConnectionTestStep,
  },
  {
    id: 'complete',
    label: 'Setup Complete',
    description: 'Your connector is ready to sync',
    icon: CheckCircleIcon,
    component: ConnectorSetupComplete,
  },
];

export const ConnectorConfigurationWizard: React.FC = () => {
  // Generate unique ID
  const wizardTitleId = useId();

  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [activeStep, setActiveStep] = useState(0);
  const [wizardData, setWizardData] = useState<Record<string, any>>({});
  const [isProcessing, setIsProcessing] = useState(false);

  const { mutateAsync: createConnectorCredentialPair } = useCreateConnectorCredentialPair();

  // Get connector and destination from URL params
  const connectorType = searchParams.get('connector');
  const destinationId = searchParams.get('destination');

  const currentStep = steps[activeStep];
  const isLastStep = activeStep === steps.length - 1;
  const isFirstStep = activeStep === 0;

  // Initialize wizard data from URL params
  useEffect(() => {
    if (connectorType && destinationId) {
      setWizardData((prev) => ({
        ...prev,
        connectorType,
        destinationId,
      }));
    }
  }, [connectorType, destinationId]);

  const handleNext = useCallback(async () => {
    if (isLastStep) {
      navigate('/connectors');
      return;
    }

    // If we're on the test step and it passed, create the connector
    if (currentStep.id === 'test' && wizardData.testPassed) {
      setIsProcessing(true);
      try {
        await createConnectorCredentialPair({
          connector_source: wizardData.connectorType,
          credential_id: wizardData.credentialId,
          destination_target_id: wizardData.destinationId,
          name: wizardData.connectorName || `${wizardData.connectorType} Connector`,
          sync_settings: wizardData.syncSettings,
        });
        setWizardData((prev) => ({ ...prev, connectorCreated: true }));
      } catch {
        setWizardData((prev) => ({
          ...prev,
          error: 'Failed to create connector. Please try again.',
        }));
        return;
      } finally {
        setIsProcessing(false);
      }
    }

    setActiveStep((prev) => prev + 1);
  }, [isLastStep, currentStep.id, wizardData, createConnectorCredentialPair, navigate]);

  const handleBack = useCallback(() => {
    if (isFirstStep) {
      navigate('/connectors');
      return;
    }
    setActiveStep((prev) => prev - 1);
  }, [isFirstStep, navigate]);

  const updateWizardData = useCallback((stepId: string, data: any) => {
    setWizardData((prev) => ({
      ...prev,
      [stepId]: data,
      // Merge step-specific data
      ...data,
    }));
  }, []);

  const canProceed = useCallback(() => {
    switch (currentStep.id) {
      case 'details': {
        return !!wizardData.connectorName && !!wizardData.connectorType;
      }
      case 'auth': {
        return !!wizardData.credentialId || wizardData.authType === 'none';
      }
      case 'sync': {
        return !!wizardData.syncSettings;
      }
      case 'test': {
        return wizardData.testPassed;
      }
      case 'complete': {
        return true;
      }
      default: {
        return false;
      }
    }
  }, [currentStep.id, wizardData]);

  if (!connectorType || !destinationId) {
    return (
      <Container maxWidth="md" sx={{ py: 4 }}>
        <Alert severity="error">
          Invalid connector configuration. Please select a connector-destination pair from the
          gallery.
        </Alert>
      </Container>
    );
  }

  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      <Box role="main" aria-labelledby="wizard-title">
        {/* Header */}
        <Box mb={4}>
          {/* Connector-Destination Pair Display */}
          <Paper elevation={1} sx={{ p: 3, mb: 3 }}>
            <Box display="flex" alignItems="center" gap={2}>
              <Avatar
                src={getConnectorLogo(connectorType)}
                alt={`${connectorType} logo`}
                sx={{ width: 48, height: 48 }}
              />
              <ArrowForwardIcon color="primary" />
              <Avatar
                src={getDestinationLogo(wizardData.destinationName || 'default')}
                alt="Destination logo"
                sx={{ width: 48, height: 48 }}
              />
              <Box flex={1}>
                <Typography variant="h6">
                  {connectorType} → {wizardData.destinationName || 'Destination'}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Setting up your connector-destination pair
                </Typography>
              </Box>
              <Chip
                label={`Step ${activeStep + 1}/${steps.length}`}
                color="primary"
                variant="outlined"
              />
            </Box>
          </Paper>

          <Typography
            id={wizardTitleId}
            variant="h3"
            component="h1"
            gutterBottom
            sx={{ fontWeight: 300, textAlign: 'center' }}
          >
            Configure Connector
          </Typography>

          {/* Progress indicator */}
          <Box sx={{ mb: 2 }}>
            <LinearProgress
              variant="determinate"
              value={(activeStep / (steps.length - 1)) * 100}
              sx={{ height: 8, borderRadius: 4 }}
              aria-label={`Setup progress: step ${activeStep + 1} of ${steps.length}`}
            />
          </Box>
        </Box>

        {/* Error Display */}
        {wizardData.error && (
          <Fade in>
            <Alert severity="error" sx={{ mb: 3 }} role="alert" aria-live="polite">
              {wizardData.error}
            </Alert>
          </Fade>
        )}

        {/* Processing Indicator */}
        {isProcessing && (
          <Fade in>
            <Alert severity="info" sx={{ mb: 3 }} role="status" aria-live="polite">
              Creating your connector...
            </Alert>
          </Fade>
        )}

        {/* Stepper */}
        <Paper elevation={1} sx={{ p: 3 }}>
          <Stepper
            activeStep={activeStep}
            orientation="vertical"
            aria-label="Connector setup steps"
          >
            {steps.map((step, index) => {
              const StepIcon = step.icon;

              return (
                <Step key={step.id}>
                  <StepLabel
                    StepIconComponent={({ active, completed }) => (
                      <Box
                        sx={{
                          width: 40,
                          height: 40,
                          borderRadius: '50%',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          bgcolor: completed
                            ? 'success.main'
                            : active
                              ? 'primary.main'
                              : 'grey.300',
                          color: completed || active ? 'white' : 'grey.600',
                        }}
                        role="img"
                        aria-label={
                          completed
                            ? `Step ${index + 1}: ${step.label} - Completed`
                            : active
                              ? `Step ${index + 1}: ${step.label} - Current step`
                              : `Step ${index + 1}: ${step.label} - Not started`
                        }
                      >
                        <StepIcon sx={{ fontSize: 20 }} />
                      </Box>
                    )}
                  >
                    <Typography variant="h6" component="h2">
                      {step.label}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {step.description}
                    </Typography>
                  </StepLabel>

                  <StepContent>
                    <Box sx={{ py: 2 }}>
                      {/* Render current step component */}
                      <step.component
                        wizardData={wizardData}
                        onDataChange={(data: any) => updateWizardData(step.id, data)}
                        onNext={handleNext}
                        onBack={handleBack}
                      />
                    </Box>
                  </StepContent>
                </Step>
              );
            })}
          </Stepper>

          {/* Navigation Buttons */}
          <Box
            sx={{
              mt: 3,
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}
          >
            <Button
              onClick={handleBack}
              startIcon={<ArrowBackIcon />}
              disabled={isProcessing}
              aria-label={isFirstStep ? 'Cancel setup' : 'Go to previous step'}
            >
              {isFirstStep ? 'Cancel' : 'Back'}
            </Button>

            <Box sx={{ flex: 1, mx: 2, textAlign: 'center' }}>
              <Typography variant="body2" color="text.secondary">
                {currentStep.description}
              </Typography>
            </Box>

            <Button
              variant="contained"
              onClick={handleNext}
              endIcon={isLastStep ? <CheckCircleIcon /> : <ArrowForwardIcon />}
              disabled={!canProceed() || isProcessing}
              aria-label={isLastStep ? 'Complete setup and continue' : 'Continue to next step'}
            >
              {isLastStep ? 'Finish' : 'Continue'}
            </Button>
          </Box>
        </Paper>

        {/* Help Text */}
        <Box sx={{ mt: 3, textAlign: 'center' }}>
          <Typography variant="body2" color="text.secondary">
            Need help? Check our{' '}
            <Button
              variant="text"
              size="small"
              href={`/docs/connectors/${connectorType}`}
              target="_blank"
              rel="noopener noreferrer"
            >
              connector setup guide
            </Button>{' '}
            or{' '}
            <Button variant="text" size="small" href="/support">
              contact support
            </Button>
          </Typography>
        </Box>
      </Box>
    </Container>
  );
};
