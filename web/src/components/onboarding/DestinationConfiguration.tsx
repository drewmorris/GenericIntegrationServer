/**
 * Destination Configuration Component
 * Dynamic form generation based on destination schema
 * Follows Material Design form patterns with comprehensive validation
 */

import {
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  ExpandMore as ExpandMoreIcon,
  Visibility as VisibilityIcon,
  VisibilityOff as VisibilityOffIcon,
} from '@mui/icons-material';
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Alert,
  Box,
  Chip,
  FormControl,
  IconButton,
  InputAdornment,
  Link,
  TextField,
  Typography,
} from '@mui/material';
import type React from 'react';
import { useCallback, useEffect, useId, useState } from 'react';

type DestinationConfigurationProps = {
  wizardData: Record<string, any>;
  onDataChange: (data: any) => void;
};

type FormField = {
  name: string;
  label: string;
  type: 'text' | 'password' | 'url' | 'number' | 'email';
  required: boolean;
  description?: string;
  placeholder?: string;
  defaultValue?: any;
  validation?: {
    pattern?: string;
    minLength?: number;
    maxLength?: number;
    min?: number;
    max?: number;
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
      defaultValue: 'https://api.cleverbrag.com',
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
  csv: [
    {
      name: 'file_path',
      label: 'Export Directory',
      type: 'text',
      required: false,
      description: 'Directory where CSV files will be saved',
      placeholder: '/exports/csv',
      defaultValue: './exports',
    },
    {
      name: 'filename_template',
      label: 'Filename Template',
      type: 'text',
      required: false,
      description: 'Template for CSV filenames (supports variables like {date}, {connector})',
      placeholder: '{connector}_{date}.csv',
      defaultValue: 'export_{date}.csv',
    },
  ],
};

export const DestinationConfiguration: React.FC<DestinationConfigurationProps> = ({
  wizardData,
  onDataChange,
}) => {
  const [formData, setFormData] = useState<Record<string, any>>(wizardData.config || {});
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [showPasswords, setShowPasswords] = useState<Record<string, boolean>>({});
  const [validationStatus, setValidationStatus] = useState<
    Record<string, 'valid' | 'invalid' | 'pending'>
  >({});

  // Generate unique IDs
  const configurationHeadingId = useId();
  const advancedConfigHeaderId = useId();

  const destinationType = wizardData.destinationType;
  const schema = destinationSchemas[destinationType] || [];
  const destinationMeta = wizardData.destinationMetadata;

  // Initialize form with default values
  useEffect(() => {
    const initialData = { ...formData };
    let hasChanges = false;

    for (const field of schema) {
      if (field.defaultValue !== undefined && !initialData[field.name]) {
        initialData[field.name] = field.defaultValue;
        hasChanges = true;
      }
    }

    if (hasChanges) {
      setFormData(initialData);
    }
  }, [schema, formData]);

  // Validate form and update parent
  useEffect(() => {
    const newErrors: Record<string, string> = {};
    const newValidationStatus: Record<string, 'valid' | 'invalid' | 'pending'> = {};

    for (const field of schema) {
      const value = formData[field.name];

      // Required field validation
      if (field.required && (!value || value.trim() === '')) {
        newErrors[field.name] = `${field.label} is required`;
        newValidationStatus[field.name] = 'invalid';
        continue;
      }

      // Skip validation for empty optional fields
      if (!value || value.trim() === '') {
        newValidationStatus[field.name] = 'valid';
        continue;
      }

      // Pattern validation
      if (field.validation?.pattern) {
        const regex = new RegExp(field.validation.pattern);
        if (!regex.test(value)) {
          newErrors[field.name] = `${field.label} format is invalid`;
          newValidationStatus[field.name] = 'invalid';
          continue;
        }
      }

      // Length validation
      if (field.validation?.minLength && value.length < field.validation.minLength) {
        newErrors[field.name] =
          `${field.label} must be at least ${field.validation.minLength} characters`;
        newValidationStatus[field.name] = 'invalid';
        continue;
      }

      if (field.validation?.maxLength && value.length > field.validation.maxLength) {
        newErrors[field.name] =
          `${field.label} must be no more than ${field.validation.maxLength} characters`;
        newValidationStatus[field.name] = 'invalid';
        continue;
      }

      // Number validation
      if (field.type === 'number') {
        const numValue = Number(value);
        if (Number.isNaN(numValue)) {
          newErrors[field.name] = `${field.label} must be a valid number`;
          newValidationStatus[field.name] = 'invalid';
          continue;
        }

        if (field.validation?.min !== undefined && numValue < field.validation.min) {
          newErrors[field.name] = `${field.label} must be at least ${field.validation.min}`;
          newValidationStatus[field.name] = 'invalid';
          continue;
        }

        if (field.validation?.max !== undefined && numValue > field.validation.max) {
          newErrors[field.name] = `${field.label} must be no more than ${field.validation.max}`;
          newValidationStatus[field.name] = 'invalid';
          continue;
        }
      }

      newValidationStatus[field.name] = 'valid';
    }

    setErrors(newErrors);
    setValidationStatus(newValidationStatus);

    const isValid = Object.keys(newErrors).length === 0;
    const hasRequiredFields = schema
      .filter((f) => f.required)
      .every((f) => formData[f.name] && formData[f.name].trim() !== '');

    onDataChange({
      config: formData,
      configValid: isValid && hasRequiredFields,
      configErrors: newErrors,
    });
  }, [formData, schema, onDataChange]);

  const handleFieldChange = useCallback((fieldName: string, value: any) => {
    setFormData((prev) => ({
      ...prev,
      [fieldName]: value,
    }));
  }, []);

  const togglePasswordVisibility = useCallback((fieldName: string) => {
    setShowPasswords((prev) => ({
      ...prev,
      [fieldName]: !prev[fieldName],
    }));
  }, []);

  const getFieldIcon = (fieldName: string) => {
    const status = validationStatus[fieldName];
    if (status === 'valid' && formData[fieldName]) {
      return <CheckCircleIcon color="success" sx={{ fontSize: 20 }} />;
    }
    if (status === 'invalid') {
      return <ErrorIcon color="error" sx={{ fontSize: 20 }} />;
    }
    return null;
  };

  if (!destinationType) {
    return (
      <Alert severity="error">
        No destination type selected. Please go back and select a destination.
      </Alert>
    );
  }

  if (schema.length === 0) {
    return (
      <Alert severity="warning">
        No configuration required for {destinationMeta?.displayName || destinationType}.
      </Alert>
    );
  }

  return (
    <Box role="region" aria-labelledby={configurationHeadingId}>
      <Typography
        id={configurationHeadingId}
        variant="h5"
        component="h2"
        gutterBottom
        sx={{ mb: 3 }}
      >
        Configure {destinationMeta?.displayName || destinationType}
      </Typography>

      <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
        Enter the connection details for your {destinationMeta?.displayName || destinationType}{' '}
        instance. All information is encrypted and stored securely.
      </Typography>

      {/* Configuration Form */}
      <Box component="form" noValidate>
        {schema.map((field) => {
          const hasError = !!errors[field.name];
          const fieldValue = formData[field.name] || '';
          const isPassword = field.type === 'password';
          const showPassword = showPasswords[field.name];

          return (
            <FormControl key={field.name} fullWidth sx={{ mb: 3 }} error={hasError}>
              <TextField
                name={field.name}
                label={field.label}
                type={isPassword && !showPassword ? 'password' : 'text'}
                value={fieldValue}
                onChange={(e) => handleFieldChange(field.name, e.target.value)}
                required={field.required}
                placeholder={field.placeholder}
                error={hasError}
                helperText={errors[field.name] || field.description}
                InputProps={{
                  endAdornment: (
                    <InputAdornment position="end">
                      {isPassword && (
                        <IconButton
                          onClick={() => togglePasswordVisibility(field.name)}
                          edge="end"
                          aria-label={showPassword ? 'Hide password' : 'Show password'}
                        >
                          {showPassword ? <VisibilityOffIcon /> : <VisibilityIcon />}
                        </IconButton>
                      )}
                      {getFieldIcon(field.name)}
                    </InputAdornment>
                  ),
                }}
                inputProps={{
                  'aria-describedby': `${field.name}-helper-text`,
                  ...(field.validation?.pattern && {
                    pattern: field.validation.pattern,
                  }),
                  ...(field.validation?.minLength && {
                    minLength: field.validation.minLength,
                  }),
                  ...(field.validation?.maxLength && {
                    maxLength: field.validation.maxLength,
                  }),
                }}
              />
            </FormControl>
          );
        })}
      </Box>

      {/* Advanced Configuration */}
      <Accordion sx={{ mt: 2 }}>
        <AccordionSummary
          expandIcon={<ExpandMoreIcon />}
          aria-controls={`${advancedConfigHeaderId}-content`}
          id={advancedConfigHeaderId}
        >
          <Typography variant="subtitle1">Advanced Configuration</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Box>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Additional settings for {destinationMeta?.displayName || destinationType} integration.
            </Typography>

            {/* Difficulty indicator */}
            <Box display="flex" alignItems="center" gap={1} mb={2}>
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
            </Box>

            {/* Help links */}
            <Box>
              <Typography variant="body2" color="text.secondary">
                Need help configuring {destinationMeta?.displayName}?
              </Typography>
              <Box sx={{ mt: 1 }}>
                <Link
                  href={`/docs/destinations/${destinationType}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  sx={{ mr: 2 }}
                >
                  Setup Guide
                </Link>
                <Link
                  href={`/docs/destinations/${destinationType}/troubleshooting`}
                  target="_blank"
                  rel="noopener noreferrer"
                  sx={{ mr: 2 }}
                >
                  Troubleshooting
                </Link>
                <Link href="/support" target="_blank" rel="noopener noreferrer">
                  Contact Support
                </Link>
              </Box>
            </Box>
          </Box>
        </AccordionDetails>
      </Accordion>

      {/* Validation Summary */}
      {Object.keys(errors).length > 0 && (
        <Alert severity="error" sx={{ mt: 3 }} role="alert">
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

      {Object.keys(errors).length === 0 && Object.keys(formData).length > 0 && (
        <Alert severity="success" sx={{ mt: 3 }} role="status">
          Configuration looks good! Click "Continue" to test the connection.
        </Alert>
      )}
    </Box>
  );
};
