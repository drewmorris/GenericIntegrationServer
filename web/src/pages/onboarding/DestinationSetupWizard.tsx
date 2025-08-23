/**
 * Destination Setup Wizard
 * Multi-step wizard for setting up the first destination
 * Follows Material Design stepper pattern with accessibility support
 */

import {
  ArrowBack as ArrowBackIcon,
  ArrowForward as ArrowForwardIcon,
  CheckCircle as CheckCircleIcon,
} from '@mui/icons-material';
import {
  Alert,
  Box,
  Button,
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
import { useCallback, useId, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { ConnectionTest } from '../../components/onboarding/ConnectionTest';
import { DestinationConfiguration } from '../../components/onboarding/DestinationConfiguration';
import { DestinationSelector } from '../../components/onboarding/DestinationSelector';
import { SetupComplete } from '../../components/onboarding/SetupComplete';
import { useCreateDestination } from '../../hooks/useCreateDestination';

type WizardStep = {
  id: string;
  label: string;
  description: string;
  component: React.ComponentType<any>;
  optional?: boolean;
};

const steps: WizardStep[] = [
  {
    id: 'select',
    label: 'Choose Destination',
    description: 'Select where you want to send your data',
    component: DestinationSelector,
  },
  {
    id: 'configure',
    label: 'Configure Connection',
    description: 'Set up the connection details',
    component: DestinationConfiguration,
  },
  {
    id: 'test',
    label: 'Test Connection',
    description: 'Verify the connection works',
    component: ConnectionTest,
  },
  {
    id: 'complete',
    label: 'Complete Setup',
    description: 'Your destination is ready to use',
    component: SetupComplete,
  },
];

export const DestinationSetupWizard: React.FC = () => {
  // Generate unique ID
  const wizardTitleId = useId();

  const navigate = useNavigate();
  const location = useLocation();
  const [activeStep, setActiveStep] = useState(0);
  const [wizardData, setWizardData] = useState<Record<string, any>>({});
  const [isProcessing, setIsProcessing] = useState(false);

  const { mutateAsync: createDestination } = useCreateDestination();

  const currentStep = steps[activeStep];
  const isLastStep = activeStep === steps.length - 1;
  const isFirstStep = activeStep === 0;

  // Get the return path from navigation state
  const returnPath = location.state?.from || '/connectors';

  const handleNext = useCallback(async () => {
    if (isLastStep) {
      // Navigate to the return path or connectors page
      navigate(returnPath);
      return;
    }

    // If we're on the test step and it passed, create the destination
    if (currentStep.id === 'test' && wizardData.testPassed) {
      setIsProcessing(true);
      try {
        await createDestination({
          name: wizardData.destinationType,
          config: wizardData.config,
        });
        setWizardData((prev) => ({ ...prev, destinationCreated: true }));
      } catch {
        setWizardData((prev) => ({
          ...prev,
          error: 'Failed to create destination. Please try again.',
        }));
        return;
      } finally {
        setIsProcessing(false);
      }
    }

    setActiveStep((prev) => prev + 1);
  }, [isLastStep, currentStep.id, wizardData, createDestination, navigate, returnPath]);

  const handleBack = useCallback(() => {
    if (isFirstStep) {
      navigate('/');
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
      case 'select': {
        return !!wizardData.destinationType;
      }
      case 'configure': {
        return !!wizardData.config && wizardData.configValid;
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

  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      <Box role="main" aria-labelledby={wizardTitleId}>
        {/* Header */}
        <Box mb={4} textAlign="center">
          <Typography
            id={wizardTitleId}
            variant="h3"
            component="h1"
            gutterBottom
            sx={{ fontWeight: 300 }}
          >
            Set Up Your First Destination
          </Typography>
          <Typography variant="h6" color="text.secondary" sx={{ mb: 3 }}>
            Before adding connectors, you need at least one destination where your data will be
            sent.
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
          <Typography variant="body2" color="text.secondary">
            Step {activeStep + 1} of {steps.length}
          </Typography>
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
              Creating your destination...
            </Alert>
          </Fade>
        )}

        {/* Stepper */}
        <Paper elevation={1} sx={{ p: 3 }}>
          <Stepper
            activeStep={activeStep}
            orientation="vertical"
            aria-label="Destination setup steps"
          >
            {steps.map((step, index) => (
              <Step key={step.id}>
                <StepLabel
                  StepIconComponent={({ active, completed }) => (
                    <Box
                      sx={{
                        width: 32,
                        height: 32,
                        borderRadius: '50%',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        bgcolor: completed ? 'success.main' : active ? 'primary.main' : 'grey.300',
                        color: completed || active ? 'white' : 'grey.600',
                        fontSize: '0.875rem',
                        fontWeight: 500,
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
                      {completed ? <CheckCircleIcon sx={{ fontSize: 20 }} /> : index + 1}
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
            ))}
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
              {isLastStep ? 'Get Started' : 'Continue'}
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
              href="/docs/destinations"
              target="_blank"
              rel="noopener noreferrer"
            >
              destination setup guide
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
