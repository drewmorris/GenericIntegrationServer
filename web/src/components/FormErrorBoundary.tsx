/**
 * FormErrorBoundary - Enhanced form error handling with validation and recovery
 * Provides user-friendly form error display and recovery options
 */

import {
  Error as ErrorIcon,
  Refresh as RefreshIcon,
  CheckCircle as ValidIcon,
  Warning as WarningIcon,
} from '@mui/icons-material';
import {
  Alert,
  AlertTitle,
  Box,
  Button,
  Collapse,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  TextField,
  TextFieldProps,
  Typography,
} from '@mui/material';
import React, { useCallback, useState } from 'react';
import { APIError } from '../lib/enhanced-api';

// Enhanced TextField with built-in validation and error display
interface ValidatedTextFieldProps extends Omit<TextFieldProps, 'error'> {
  validation?: {
    required?: boolean;
    minLength?: number;
    maxLength?: number;
    pattern?: RegExp;
    validator?: (value: string) => string | null;
  };
  showValidation?: boolean;
  onValidChange?: (isValid: boolean, error?: string) => void;
  error?: string | null;
}

export const ValidatedTextField: React.FC<ValidatedTextFieldProps> = ({
  validation,
  showValidation = false,
  onValidChange,
  value,
  onChange,
  error: externalError,
  ...props
}) => {
  const [internalError, setInternalError] = useState<string | null>(null);
  const [touched, setTouched] = useState(false);

  // Use external error if provided, otherwise use internal error
  const error = externalError !== undefined ? externalError : internalError;

  const validateValue = useCallback(
    (val: string): string | null => {
      if (!validation) return null;

      if (validation.required && !val.trim()) {
        return 'This field is required';
      }

      if (validation.minLength && val.length < validation.minLength) {
        return `Must be at least ${validation.minLength} characters`;
      }

      if (validation.maxLength && val.length > validation.maxLength) {
        return `Must be no more than ${validation.maxLength} characters`;
      }

      if (validation.pattern && !validation.pattern.test(val)) {
        return 'Invalid format';
      }

      if (validation.validator) {
        return validation.validator(val);
      }

      return null;
    },
    [validation],
  );

  const handleChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = event.target.value;

    // Only validate internally if no external error is provided
    if (externalError === undefined) {
      const validationError = validateValue(newValue);
      setInternalError(validationError);

      if (onValidChange) {
        onValidChange(!validationError, validationError || undefined);
      }
    }

    if (onChange) {
      onChange(event);
    }
  };

  const handleBlur = (event: React.FocusEvent<HTMLInputElement>) => {
    setTouched(true);
    if (props.onBlur) {
      props.onBlur(event);
    }
  };

  const showError = externalError !== undefined ? !!externalError : touched && internalError;
  const showSuccess = showValidation && touched && !error && value;

  return (
    <TextField
      {...props}
      value={value}
      onChange={handleChange}
      onBlur={handleBlur}
      error={!!showError}
      helperText={showError || props.helperText}
      InputProps={{
        ...props.InputProps,
        endAdornment:
          showValidation &&
          touched &&
          (showError ? (
            <ErrorIcon color="error" fontSize="small" />
          ) : showSuccess ? (
            <ValidIcon color="success" fontSize="small" />
          ) : null),
      }}
    />
  );
};

// Wrapper component for ValidatedTextField that works with form validation hooks
interface FormTextFieldProps<T extends string = string>
  extends Omit<ValidatedTextFieldProps, 'onChange' | 'onBlur'> {
  name: T;
  onChange: (field: T, value: any) => void;
  onBlur: (field: T) => void;
}

export const FormTextField = <T extends string = string>({
  name,
  onChange,
  onBlur,
  ...props
}: FormTextFieldProps<T>) => {
  const handleChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    onChange(name, event.target.value);
  };

  const handleBlur = () => {
    onBlur(name);
  };

  return <ValidatedTextField {...props} onChange={handleChange} onBlur={handleBlur} />;
};

// Form-level error handling component
interface FormErrorDisplayProps {
  errors: Record<string, string | string[]>;
  serverError?: Error | APIError | null;
  onRetry?: () => void;
  onClearErrors?: () => void;
  showFieldErrors?: boolean;
}

export const FormErrorDisplay: React.FC<FormErrorDisplayProps> = ({
  errors,
  serverError,
  onRetry,
  onClearErrors,
  showFieldErrors = true,
}) => {
  const [expanded, setExpanded] = useState(true);

  const fieldErrors = Object.entries(errors).filter(([, error]) => error);
  const hasFieldErrors = fieldErrors.length > 0;
  const hasServerError = serverError !== null && serverError !== undefined;

  if (!hasFieldErrors && !hasServerError) {
    return null;
  }

  const renderFieldErrors = () => {
    if (!showFieldErrors || !hasFieldErrors) {
      return null;
    }

    return (
      <Box sx={{ mt: 1 }}>
        <Typography variant="subtitle2" color="error" gutterBottom>
          Please fix the following errors:
        </Typography>
        <List dense>
          {fieldErrors.map(([field, error]) => {
            const errorMessages = Array.isArray(error) ? error : [error];
            return errorMessages.map((msg) => (
              <ListItem key={`${field}-${msg}`} sx={{ py: 0.5, pl: 0 }}>
                <ListItemIcon sx={{ minWidth: 32 }}>
                  <ErrorIcon color="error" fontSize="small" />
                </ListItemIcon>
                <ListItemText
                  primary={msg}
                  primaryTypographyProps={{ variant: 'body2', color: 'error' }}
                />
              </ListItem>
            ));
          })}
        </List>
      </Box>
    );
  };

  const renderServerError = () => {
    if (!hasServerError) {
      return null;
    }

    const isAPIError = serverError instanceof APIError;
    const message = isAPIError
      ? serverError.userMessage || serverError.message
      : serverError.message;

    return (
      <Alert
        severity={isAPIError && serverError.retryable ? 'warning' : 'error'}
        sx={{ mt: hasFieldErrors ? 2 : 0 }}
        action={
          isAPIError &&
          serverError.retryable &&
          onRetry && (
            <Button color="inherit" size="small" startIcon={<RefreshIcon />} onClick={onRetry}>
              Try Again
            </Button>
          )
        }
      >
        <AlertTitle>{isAPIError && serverError.retryable ? 'Temporary Error' : 'Error'}</AlertTitle>
        {message}
      </Alert>
    );
  };

  return (
    <Box>
      {renderServerError()}

      {hasFieldErrors && (
        <Box>
          <Button
            size="small"
            variant="text"
            onClick={() => setExpanded(!expanded)}
            startIcon={<WarningIcon color="warning" />}
            sx={{ mt: hasServerError ? 1 : 0, mb: 0.5 }}
          >
            {fieldErrors.length} validation {fieldErrors.length === 1 ? 'error' : 'errors'}
          </Button>

          <Collapse in={expanded}>{renderFieldErrors()}</Collapse>
        </Box>
      )}

      {(hasFieldErrors || hasServerError) && onClearErrors && (
        <Box sx={{ mt: 1 }}>
          <Button size="small" variant="outlined" color="primary" onClick={onClearErrors}>
            Clear Errors
          </Button>
        </Box>
      )}
    </Box>
  );
};

// Hook for form validation state management
export const useFormValidation = <T extends Record<string, any>>(
  initialValues: T,
  validators?: Partial<Record<keyof T, (value: any) => string | null>>,
) => {
  const [values, setValues] = useState<T>(initialValues);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [touched, setTouched] = useState<Record<string, boolean>>({});
  const [isValidating, setIsValidating] = useState(false);

  const validateField = useCallback(
    (field: keyof T, value: any): string | null => {
      const validator = validators?.[field];
      return validator ? validator(value) : null;
    },
    [validators],
  );

  const validateAllFields = useCallback((): boolean => {
    const newErrors: Record<string, string> = {};
    let isValid = true;

    Object.keys(values).forEach((field) => {
      const error = validateField(field, values[field]);
      if (error) {
        newErrors[field] = error;
        isValid = false;
      }
    });

    setErrors(newErrors);
    return isValid;
  }, [values, validateField]);

  const handleChange = useCallback(
    (field: keyof T, value: any) => {
      setValues((prev) => ({ ...prev, [field]: value }));

      // Validate field if it's been touched
      if (touched[field as string]) {
        const error = validateField(field, value);
        setErrors((prev) => ({
          ...prev,
          [field]: error || '',
        }));
      }
    },
    [touched, validateField],
  );

  const handleBlur = useCallback(
    (field: keyof T) => {
      setTouched((prev) => ({ ...prev, [field]: true }));

      // Validate on blur
      const error = validateField(field, values[field]);
      setErrors((prev) => ({
        ...prev,
        [field]: error || '',
      }));
    },
    [values, validateField],
  );

  const clearErrors = useCallback(() => {
    setErrors({});
    setTouched({});
  }, []);

  const reset = useCallback(() => {
    setValues(initialValues);
    setErrors({});
    setTouched({});
    setIsValidating(false);
  }, [initialValues]);

  return {
    values,
    errors,
    touched,
    isValidating,
    setIsValidating,
    handleChange,
    handleBlur,
    validateAllFields,
    clearErrors,
    reset,
    isValid: Object.keys(errors).length === 0,
  };
};
