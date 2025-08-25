/**
 * ErrorDisplay - Consistent error UI components for different error scenarios
 * Provides user-friendly error messages with recovery actions
 */

import {
  BugReport as BugIcon,
  ExpandLess as CollapseIcon,
  ErrorOutline as ErrorIcon,
  ExpandMore as ExpandIcon,
  Wifi as NetworkIcon,
  Refresh as RefreshIcon,
  Security as SecurityIcon,
  Warning as WarningIcon,
} from '@mui/icons-material';
import {
  Alert,
  AlertTitle,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Collapse,
  Stack,
  SxProps,
  Theme,
  Typography,
} from '@mui/material';
import React from 'react';

import { APIError } from '../lib/enhanced-api';

interface ErrorDisplayProps {
  error: Error | APIError | string;
  title?: string;
  variant?: 'alert' | 'card' | 'inline';
  severity?: 'error' | 'warning' | 'info';
  showRetry?: boolean;
  showDetails?: boolean;
  onRetry?: () => void;
  onDismiss?: () => void;
  className?: string;
  actions?: React.ReactNode;
  sx?: SxProps<Theme>;
}

const getErrorIcon = (error: Error | APIError | string) => {
  if (typeof error === 'string') {
    return <ErrorIcon />;
  }

  if (error instanceof APIError) {
    switch (error.statusCode) {
      case 401:
      case 403:
        return <SecurityIcon />;
      case 429:
      case 500:
      case 502:
      case 503:
      case 504:
        return <NetworkIcon />;
      default:
        return error.retryable ? <WarningIcon /> : <ErrorIcon />;
    }
  }

  return <ErrorIcon />;
};

const getErrorSeverity = (error: Error | APIError | string): 'error' | 'warning' | 'info' => {
  if (typeof error === 'string') {
    return 'error';
  }

  if (error instanceof APIError) {
    if (error.retryable) {
      return 'warning';
    }

    switch (error.statusCode) {
      case 401:
      case 403:
        return 'warning';
      case 404:
        return 'info';
      default:
        return 'error';
    }
  }

  return 'error';
};

const getErrorMessage = (error: Error | APIError | string): string => {
  if (typeof error === 'string') {
    return error;
  }

  if (error instanceof APIError && error.userMessage) {
    return error.userMessage;
  }

  return error.message || 'An unexpected error occurred';
};

const getErrorTitle = (error: Error | APIError | string): string => {
  if (typeof error === 'string') {
    return 'Error';
  }

  if (error instanceof APIError) {
    switch (error.statusCode) {
      case 400:
        return 'Invalid Request';
      case 401:
        return 'Authentication Required';
      case 403:
        return 'Access Denied';
      case 404:
        return 'Not Found';
      case 409:
        return 'Conflict';
      case 422:
        return 'Validation Error';
      case 429:
        return 'Rate Limited';
      case 500:
        return 'Server Error';
      case 502:
      case 503:
      case 504:
        return 'Service Unavailable';
      default:
        return error.retryable ? 'Temporary Error' : 'Error';
    }
  }

  return 'Error';
};

export const ErrorDisplay: React.FC<ErrorDisplayProps> = ({
  error,
  title,
  variant = 'alert',
  severity,
  showRetry = true,
  showDetails = false,
  onRetry,
  onDismiss,
  className,
  actions,
  sx,
}) => {
  const [detailsExpanded, setDetailsExpanded] = React.useState(false);

  const errorMessage = getErrorMessage(error);
  const errorTitle = title || getErrorTitle(error);
  const errorSeverity = severity || getErrorSeverity(error);
  const isRetryable = error instanceof APIError ? error.retryable : true;
  const icon = getErrorIcon(error);

  const handleRetry = () => {
    if (onRetry) {
      onRetry();
    }
  };

  const toggleDetails = () => {
    setDetailsExpanded((prev) => !prev);
  };

  const renderActions = () => (
    <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
      {showRetry && isRetryable && onRetry && (
        <Button
          size="small"
          variant="outlined"
          startIcon={<RefreshIcon />}
          onClick={handleRetry}
          color={errorSeverity === 'error' ? 'error' : 'primary'}
        >
          Try Again
        </Button>
      )}

      {showDetails && error instanceof Error && (
        <Button
          size="small"
          variant="text"
          startIcon={<BugIcon />}
          endIcon={detailsExpanded ? <CollapseIcon /> : <ExpandIcon />}
          onClick={toggleDetails}
          color={errorSeverity === 'error' ? 'error' : 'primary'}
        >
          {detailsExpanded ? 'Hide' : 'Show'} Details
        </Button>
      )}

      {actions}
    </Stack>
  );

  const renderDetails = () => {
    if (!showDetails || typeof error === 'string' || !detailsExpanded) {
      return null;
    }

    return (
      <Collapse in={detailsExpanded}>
        <Box sx={{ mt: 2, p: 2, backgroundColor: 'action.hover', borderRadius: 1 }}>
          <Typography variant="subtitle2" gutterBottom>
            Technical Details:
          </Typography>
          <Typography
            variant="body2"
            component="pre"
            sx={{
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
              fontSize: '0.75rem',
              maxHeight: 200,
              overflow: 'auto',
            }}
          >
            {error.stack || error.message}
          </Typography>

          {error instanceof APIError && error.statusCode && (
            <Box sx={{ mt: 1 }}>
              <Chip
                label={`HTTP ${error.statusCode}`}
                size="small"
                color={errorSeverity}
                variant="outlined"
              />
            </Box>
          )}
        </Box>
      </Collapse>
    );
  };

  // Render based on variant
  switch (variant) {
    case 'card':
      return (
        <Card
          className={className}
          sx={{ border: `1px solid`, borderColor: `${errorSeverity}.main`, ...sx }}
        >
          <CardContent>
            <Stack direction="row" spacing={2} alignItems="flex-start">
              {React.cloneElement(icon as React.ReactElement, {
                color: errorSeverity,
                sx: { mt: 0.5 },
              })}

              <Box sx={{ flex: 1 }}>
                <Typography variant="h6" color={`${errorSeverity}.main`} gutterBottom>
                  {errorTitle}
                </Typography>
                <Typography variant="body2" color="text.secondary" paragraph>
                  {errorMessage}
                </Typography>

                {renderActions()}
                {renderDetails()}
              </Box>
            </Stack>
          </CardContent>
        </Card>
      );

    case 'inline':
      return (
        <Box className={className} sx={{ display: 'flex', alignItems: 'center', gap: 1, ...sx }}>
          {React.cloneElement(icon as React.ReactElement, {
            color: errorSeverity,
            fontSize: 'small',
          })}
          <Typography variant="body2" color={`${errorSeverity}.main`}>
            {errorMessage}
          </Typography>
          {showRetry && isRetryable && onRetry && (
            <Button
              size="small"
              variant="text"
              onClick={handleRetry}
              color={errorSeverity}
              startIcon={<RefreshIcon fontSize="small" />}
            >
              Retry
            </Button>
          )}
        </Box>
      );

    default: // alert
      return (
        <Alert
          severity={errorSeverity}
          className={className}
          onClose={onDismiss}
          action={renderActions()}
          sx={sx}
        >
          <AlertTitle>{errorTitle}</AlertTitle>
          {errorMessage}
          {renderDetails()}
        </Alert>
      );
  }
};

// Convenience components for specific error types
export const NetworkErrorDisplay: React.FC<
  Omit<ErrorDisplayProps, 'error'> & { onRetry: () => void }
> = (props) => (
  <ErrorDisplay
    error={
      new APIError(
        'Network connection failed',
        undefined,
        'Please check your internet connection and try again',
        true,
      )
    }
    title="Connection Error"
    showRetry={true}
    {...props}
  />
);

export const NotFoundDisplay: React.FC<Omit<ErrorDisplayProps, 'error'>> = (props) => (
  <ErrorDisplay
    error={
      new APIError('Resource not found', 404, 'The requested resource could not be found', false)
    }
    title="Not Found"
    severity="info"
    showRetry={false}
    {...props}
  />
);

export const UnauthorizedDisplay: React.FC<Omit<ErrorDisplayProps, 'error'>> = (props) => (
  <ErrorDisplay
    error={new APIError('Unauthorized', 401, 'Please log in to access this resource', false)}
    title="Authentication Required"
    severity="warning"
    showRetry={false}
    {...props}
  />
);
