/**
 * Destination Edit Dialog
 * Comprehensive destination configuration editor with validation
 * Supports dynamic schema-based forms and connection testing
 */

import {
  Close as CloseIcon,
  ExpandMore as ExpandMoreIcon,
  Save as SaveIcon,
  Science as TestTubeIcon,
  Visibility as VisibilityIcon,
  VisibilityOff as VisibilityOffIcon,
} from '@mui/icons-material';
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  FormControlLabel,
  FormHelperText,
  Grid,
  IconButton,
  InputAdornment,
  Switch,
  Tab,
  Tabs,
  TextField,
  Typography,
} from '@mui/material';
import type React from 'react';
import { useCallback, useEffect, useId, useState } from 'react';
import { useTestDestination } from '../../hooks/useTestDestination';
import { useUpdateDestinationTarget } from '../../hooks/useUpdateDestination';

// Validation helper functions
const validateField = (
  field: {
    name: string;
    label: string;
    required?: boolean;
    validation?: { pattern?: string; minLength?: number; maxLength?: number };
  },
  value: string,
): string | null => {
  // Required field validation
  if (field.required && (!value || value.trim() === '')) {
    return `${field.label} is required`;
  }

  // Skip validation for empty optional fields
  if (!value || value.trim() === '') {
    return null;
  }

  // Pattern validation
  if (field.validation?.pattern) {
    const regex = new RegExp(field.validation.pattern);
    if (!regex.test(value)) {
      return `${field.label} format is invalid`;
    }
  }

  // Length validation
  if (field.validation?.minLength && value.length < field.validation.minLength) {
    return `${field.label} must be at least ${field.validation.minLength} characters`;
  }

  if (field.validation?.maxLength && value.length > field.validation.maxLength) {
    return `${field.label} must be no more than ${field.validation.maxLength} characters`;
  }

  return null;
};

type DestinationEditDialogProps = {
  destination: {
    id: string;
    name: string;
    displayName?: string;
    config: Record<string, any>;
    status: string;
  };
  open: boolean;
  onClose: () => void;
  onSave: () => void;
};

type FormField = {
  name: string;
  label: string;
  type: 'text' | 'password' | 'url' | 'number' | 'boolean';
  required: boolean;
  description?: string;
  placeholder?: string;
  validation?: {
    pattern?: string;
    minLength?: number;
    maxLength?: number;
  };
};

// Schema definitions for each destination type
const destinationSchemas: Record<string, FormField[]> = {
  cleverbrag: [
    {
      name: 'api_key',
      label: 'API Key',
      type: 'password',
      required: true,
      description: 'Your CleverBrag API key for authentication',
      placeholder: 'cb_live_...',
      validation: {
        pattern: '^cb_(live|test)_[a-zA-Z0-9]{32,}$',
        minLength: 40,
      },
    },
    {
      name: 'base_url',
      label: 'Base URL',
      type: 'url',
      required: false,
      description: 'CleverBrag instance URL (leave empty for default)',
      placeholder: 'https://your-instance.cleverbrag.com',
      validation: {
        pattern: '^https?://.+',
      },
    },
  ],
  onyx: [
    {
      name: 'base_url',
      label: 'Onyx Server URL',
      type: 'url',
      required: true,
      description: 'URL of your Onyx server instance',
      placeholder: 'https://onyx.yourcompany.com',
      validation: {
        pattern: '^https?://.+',
      },
    },
    {
      name: 'api_key',
      label: 'API Key',
      type: 'password',
      required: false,
      description: 'API key for authentication (if required)',
      placeholder: 'Optional API key',
    },
  ],
};

export const DestinationEditDialog: React.FC<DestinationEditDialogProps> = ({
  destination,
  open,
  onClose,
  onSave,
}) => {
  const [activeTab, setActiveTab] = useState(0);
  const [formData, setFormData] = useState<Record<string, any>>(destination.config);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [showPasswords, setShowPasswords] = useState<Record<string, boolean>>({});
  const [isTestingConnection, setIsTestingConnection] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

  // Generate unique IDs
  const editDialogTitleId = useId();
  const timeoutSettingsHeaderId = useId();
  const retrySettingsHeaderId = useId();
  const batchSettingsHeaderId = useId();

  const { mutateAsync: updateDestination, isPending: isSaving } = useUpdateDestinationTarget();
  const { mutateAsync: testDestination } = useTestDestination();

  const schema = destinationSchemas[destination.name] || [];

  // Track changes
  useEffect(() => {
    const hasChanges = JSON.stringify(formData) !== JSON.stringify(destination.config);
    setHasUnsavedChanges(hasChanges);
  }, [formData, destination.config]);

  // Validate form
  const validateForm = useCallback(() => {
    const newErrors: Record<string, string> = {};

    for (const field of schema) {
      const value = formData[field.name];
      const error = validateField(field, value);
      if (error) {
        newErrors[field.name] = error;
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }, [formData, schema]);

  const handleFieldChange = useCallback(
    (fieldName: string, value: string | number | boolean) => {
      setFormData((prev) => ({
        ...prev,
        [fieldName]: value,
      }));

      // Clear field error when user starts typing
      if (errors[fieldName]) {
        setErrors((prev) => {
          const newErrors = { ...prev };
          delete newErrors[fieldName];
          return newErrors;
        });
      }
    },
    [errors],
  );

  const togglePasswordVisibility = useCallback((fieldName: string) => {
    setShowPasswords((prev) => ({
      ...prev,
      [fieldName]: !prev[fieldName],
    }));
  }, []);

  const handleTestConnection = async () => {
    if (!validateForm()) {
      return;
    }

    setIsTestingConnection(true);
    setTestResult(null);

    try {
      const result = await testDestination({
        name: destination.name,
        config: formData,
      });

      setTestResult({
        success: result.success,
        message: result.message,
      });
    } catch (error) {
      setTestResult({
        success: false,
        message: error instanceof Error ? error.message : 'Connection test failed',
      });
    } finally {
      setIsTestingConnection(false);
    }
  };

  const handleSave = async () => {
    if (!validateForm()) {
      return;
    }

    try {
      await updateDestination({
        id: destination.id,
        config: formData,
      });

      onSave();
    } catch (error) {
      console.error('Failed to update destination:', error);
    }
  };

  const handleClose = () => {
    if (
      hasUnsavedChanges &&
      !window.confirm('You have unsaved changes. Are you sure you want to close?')
    ) {
      return;
    }
    onClose();
  };

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
  };

  const isFormValid =
    Object.keys(errors).length === 0 &&
    schema
      .filter((f) => f.required)
      .every((f) => formData[f.name] && formData[f.name].trim() !== '');

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth="md"
      fullWidth
      aria-labelledby={editDialogTitleId}
    >
      <DialogTitle>
        <Box display="flex" alignItems="center" justifyContent="space-between">
          <Typography variant="h6" component="h2" id={editDialogTitleId}>
            Edit {destination.displayName || destination.name}
          </Typography>
          <Box display="flex" alignItems="center" gap={1}>
            {hasUnsavedChanges && (
              <Chip label="Unsaved changes" size="small" color="warning" variant="outlined" />
            )}
            <IconButton onClick={handleClose} size="small" aria-label="Close dialog">
              <CloseIcon />
            </IconButton>
          </Box>
        </Box>
      </DialogTitle>

      <DialogContent>
        <Tabs value={activeTab} onChange={handleTabChange} sx={{ mb: 3 }}>
          <Tab label="Configuration" />
          <Tab label="Advanced Settings" />
        </Tabs>

        {activeTab === 0 && (
          <Box>
            {/* Connection Test Result */}
            {testResult && (
              <Alert
                severity={testResult.success ? 'success' : 'error'}
                sx={{ mb: 3 }}
                action={
                  <Button color="inherit" size="small" onClick={() => setTestResult(null)}>
                    Dismiss
                  </Button>
                }
              >
                {testResult.message}
              </Alert>
            )}

            {/* Configuration Form */}
            <Box component="form" noValidate>
              {schema.map((field) => {
                const hasError = !!errors[field.name];
                const fieldValue = formData[field.name] || '';
                const isPassword = field.type === 'password';
                const showPassword = showPasswords[field.name];

                if (field.type === 'boolean') {
                  return (
                    <FormControl key={field.name} fullWidth sx={{ mb: 3 }}>
                      <FormControlLabel
                        control={
                          <Switch
                            checked={Boolean(fieldValue)}
                            onChange={(e) => handleFieldChange(field.name, e.target.checked)}
                            name={field.name}
                          />
                        }
                        label={field.label}
                      />
                      {field.description && <FormHelperText>{field.description}</FormHelperText>}
                    </FormControl>
                  );
                }

                return (
                  <FormControl key={field.name} fullWidth sx={{ mb: 3 }} error={hasError}>
                    <TextField
                      name={field.name}
                      label={field.label}
                      type={isPassword && !showPassword ? 'password' : field.type}
                      value={fieldValue}
                      onChange={(e) => handleFieldChange(field.name, e.target.value)}
                      required={field.required}
                      placeholder={field.placeholder}
                      error={hasError}
                      helperText={errors[field.name] || field.description}
                      InputProps={{
                        endAdornment: isPassword ? (
                          <InputAdornment position="end">
                            <IconButton
                              onClick={() => togglePasswordVisibility(field.name)}
                              edge="end"
                              aria-label={showPassword ? 'Hide password' : 'Show password'}
                            >
                              {showPassword ? <VisibilityOffIcon /> : <VisibilityIcon />}
                            </IconButton>
                          </InputAdornment>
                        ) : undefined,
                      }}
                    />
                  </FormControl>
                );
              })}
            </Box>

            {/* Test Connection */}
            <Box sx={{ mt: 3 }}>
              <Button
                variant="outlined"
                onClick={handleTestConnection}
                disabled={!isFormValid || isTestingConnection}
                startIcon={isTestingConnection ? <CircularProgress size={20} /> : <TestTubeIcon />}
                fullWidth
              >
                {isTestingConnection ? 'Testing Connection...' : 'Test Connection'}
              </Button>
            </Box>
          </Box>
        )}

        {activeTab === 1 && (
          <Box>
            <Typography variant="h6" gutterBottom>
              Advanced Settings
            </Typography>

            <Accordion>
              <AccordionSummary
                expandIcon={<ExpandMoreIcon />}
                aria-controls="timeout-settings-content"
                id={timeoutSettingsHeaderId}
              >
                <Typography>Timeout Settings</Typography>
              </AccordionSummary>
              <AccordionDetails>
                <Grid container spacing={2}>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      fullWidth
                      label="Connection Timeout (seconds)"
                      type="number"
                      value={formData.connection_timeout || 30}
                      onChange={(e) =>
                        handleFieldChange('connection_timeout', Number.parseInt(e.target.value, 10))
                      }
                      inputProps={{ min: 1, max: 300 }}
                    />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      fullWidth
                      label="Request Timeout (seconds)"
                      type="number"
                      value={formData.request_timeout || 60}
                      onChange={(e) =>
                        handleFieldChange('request_timeout', Number.parseInt(e.target.value, 10))
                      }
                      inputProps={{ min: 1, max: 600 }}
                    />
                  </Grid>
                </Grid>
              </AccordionDetails>
            </Accordion>

            <Accordion>
              <AccordionSummary
                expandIcon={<ExpandMoreIcon />}
                aria-controls="retry-settings-content"
                id={retrySettingsHeaderId}
              >
                <Typography>Retry Settings</Typography>
              </AccordionSummary>
              <AccordionDetails>
                <Grid container spacing={2}>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      fullWidth
                      label="Max Retries"
                      type="number"
                      value={formData.max_retries || 3}
                      onChange={(e) =>
                        handleFieldChange('max_retries', Number.parseInt(e.target.value, 10))
                      }
                      inputProps={{ min: 0, max: 10 }}
                    />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      fullWidth
                      label="Retry Delay (seconds)"
                      type="number"
                      value={formData.retry_delay || 1}
                      onChange={(e) =>
                        handleFieldChange('retry_delay', Number.parseInt(e.target.value, 10))
                      }
                      inputProps={{ min: 1, max: 60 }}
                    />
                  </Grid>
                </Grid>
              </AccordionDetails>
            </Accordion>

            <Accordion>
              <AccordionSummary
                expandIcon={<ExpandMoreIcon />}
                aria-controls="batch-settings-content"
                id={batchSettingsHeaderId}
              >
                <Typography>Batch Processing</Typography>
              </AccordionSummary>
              <AccordionDetails>
                <Grid container spacing={2}>
                  <Grid item xs={12}>
                    <FormControlLabel
                      control={
                        <Switch
                          checked={Boolean(formData.enable_batching)}
                          onChange={(e) => handleFieldChange('enable_batching', e.target.checked)}
                        />
                      }
                      label="Enable Batch Processing"
                    />
                  </Grid>
                  {formData.enable_batching && (
                    <>
                      <Grid item xs={12} sm={6}>
                        <TextField
                          fullWidth
                          label="Batch Size"
                          type="number"
                          value={formData.batch_size || 100}
                          onChange={(e) =>
                            handleFieldChange('batch_size', Number.parseInt(e.target.value, 10))
                          }
                          inputProps={{ min: 1, max: 1000 }}
                        />
                      </Grid>
                      <Grid item xs={12} sm={6}>
                        <TextField
                          fullWidth
                          label="Batch Timeout (seconds)"
                          type="number"
                          value={formData.batch_timeout || 30}
                          onChange={(e) =>
                            handleFieldChange('batch_timeout', Number.parseInt(e.target.value, 10))
                          }
                          inputProps={{ min: 1, max: 300 }}
                        />
                      </Grid>
                    </>
                  )}
                </Grid>
              </AccordionDetails>
            </Accordion>
          </Box>
        )}

        {/* Validation Summary */}
        {Object.keys(errors).length > 0 && (
          <Alert severity="error" sx={{ mt: 3 }}>
            <Typography variant="body2" sx={{ mb: 1 }}>
              Please fix the following issues:
            </Typography>
            <ul style={{ margin: 0, paddingLeft: 20 }}>
              {Object.entries(errors).map(([field, error]) => (
                <li key={field}>
                  <Typography variant="body2">{error}</Typography>
                </li>
              ))}
            </ul>
          </Alert>
        )}
      </DialogContent>

      <DialogActions>
        <Button onClick={handleClose}>Cancel</Button>
        <Button
          variant="contained"
          onClick={handleSave}
          disabled={!isFormValid || isSaving}
          startIcon={isSaving ? <CircularProgress size={20} /> : <SaveIcon />}
        >
          {isSaving ? 'Saving...' : 'Save Changes'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};
