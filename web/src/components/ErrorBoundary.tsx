/**
 * ErrorBoundary - Catches React component errors and provides graceful fallback UI
 * Prevents white screen of death and provides recovery options
 */

import {
  BugReport as BugIcon,
  ExpandLess as CollapseIcon,
  ErrorOutline as ErrorIcon,
  ExpandMore as ExpandIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material';
import {
  Alert,
  AlertTitle,
  Box,
  Button,
  Card,
  CardContent,
  Collapse,
  Container,
  Stack,
  Typography,
} from '@mui/material';
import React, { Component, type ErrorInfo, type ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
  showDetails: boolean;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      showDetails: false,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return {
      hasError: true,
      error,
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    this.setState({
      error,
      errorInfo,
    });

    // Log error to console for development
    console.error('ErrorBoundary caught an error:', error, errorInfo);

    // Call custom error handler if provided
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }

    // In production, you might want to send this to an error reporting service
    // e.g., Sentry, LogRocket, etc.
  }

  handleRetry = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
      showDetails: false,
    });
  };

  handleReload = () => {
    window.location.reload();
  };

  toggleDetails = () => {
    this.setState((prev) => ({ showDetails: !prev.showDetails }));
  };

  render() {
    if (this.state.hasError) {
      // Custom fallback UI can be provided
      if (this.props.fallback) {
        return this.props.fallback;
      }

      // Default error UI
      return (
        <Container maxWidth="md" sx={{ mt: 4, mb: 4 }}>
          <Card>
            <CardContent>
              <Stack spacing={3} alignItems="center" textAlign="center">
                <ErrorIcon color="error" sx={{ fontSize: 64 }} />

                <Box>
                  <Typography variant="h4" gutterBottom color="error">
                    Something went wrong
                  </Typography>
                  <Typography variant="body1" color="text.secondary">
                    The application encountered an unexpected error. You can try to recover by
                    retrying the operation or refreshing the page.
                  </Typography>
                </Box>

                {/* Action buttons */}
                <Stack direction="row" spacing={2}>
                  <Button
                    variant="contained"
                    startIcon={<RefreshIcon />}
                    onClick={this.handleRetry}
                    color="primary"
                  >
                    Try Again
                  </Button>
                  <Button variant="outlined" onClick={this.handleReload} color="primary">
                    Reload Page
                  </Button>
                </Stack>

                {/* Error details (collapsible) */}
                <Box width="100%">
                  <Button
                    startIcon={<BugIcon />}
                    endIcon={this.state.showDetails ? <CollapseIcon /> : <ExpandIcon />}
                    onClick={this.toggleDetails}
                    color="error"
                    variant="text"
                    size="small"
                  >
                    {this.state.showDetails ? 'Hide' : 'Show'} Technical Details
                  </Button>

                  <Collapse in={this.state.showDetails}>
                    <Alert severity="error" sx={{ mt: 2, textAlign: 'left' }}>
                      <AlertTitle>Error Details</AlertTitle>

                      {this.state.error && (
                        <Box sx={{ mb: 2 }}>
                          <Typography variant="subtitle2" gutterBottom>
                            Error Message:
                          </Typography>
                          <Typography
                            variant="body2"
                            component="pre"
                            sx={{
                              whiteSpace: 'pre-wrap',
                              wordBreak: 'break-word',
                              fontSize: '0.75rem',
                              backgroundColor: 'rgba(0,0,0,0.04)',
                              p: 1,
                              borderRadius: 1,
                            }}
                          >
                            {this.state.error.message}
                          </Typography>
                        </Box>
                      )}

                      {this.state.error?.stack && (
                        <Box sx={{ mb: 2 }}>
                          <Typography variant="subtitle2" gutterBottom>
                            Stack Trace:
                          </Typography>
                          <Typography
                            variant="body2"
                            component="pre"
                            sx={{
                              whiteSpace: 'pre-wrap',
                              wordBreak: 'break-word',
                              fontSize: '0.75rem',
                              backgroundColor: 'rgba(0,0,0,0.04)',
                              p: 1,
                              borderRadius: 1,
                              maxHeight: 200,
                              overflow: 'auto',
                            }}
                          >
                            {this.state.error.stack}
                          </Typography>
                        </Box>
                      )}

                      {this.state.errorInfo?.componentStack && (
                        <Box>
                          <Typography variant="subtitle2" gutterBottom>
                            Component Stack:
                          </Typography>
                          <Typography
                            variant="body2"
                            component="pre"
                            sx={{
                              whiteSpace: 'pre-wrap',
                              wordBreak: 'break-word',
                              fontSize: '0.75rem',
                              backgroundColor: 'rgba(0,0,0,0.04)',
                              p: 1,
                              borderRadius: 1,
                              maxHeight: 200,
                              overflow: 'auto',
                            }}
                          >
                            {this.state.errorInfo.componentStack}
                          </Typography>
                        </Box>
                      )}
                    </Alert>
                  </Collapse>
                </Box>

                {/* Contact support hint */}
                <Typography variant="caption" color="text.secondary">
                  If this problem persists, please contact support with the technical details above.
                </Typography>
              </Stack>
            </CardContent>
          </Card>
        </Container>
      );
    }

    return this.props.children;
  }
}

// HOC for easier usage
export const withErrorBoundary = <P extends object>(
  Component: React.ComponentType<P>,
  errorBoundaryProps?: Omit<Props, 'children'>,
) => {
  const WrappedComponent = (props: P) => (
    <ErrorBoundary {...errorBoundaryProps}>
      <Component {...props} />
    </ErrorBoundary>
  );

  WrappedComponent.displayName = `withErrorBoundary(${Component.displayName || Component.name})`;

  return WrappedComponent;
};
