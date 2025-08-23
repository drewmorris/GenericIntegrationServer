/**
 * Destination Guard Component
 * Ensures users have at least one destination configured before accessing connector features
 * Follows WCAG 2.1 AA accessibility standards and Material Design principles
 */

import { Alert, Box, CircularProgress } from '@mui/material';
import type React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useDestinations } from '../hooks/useDestinations';

type DestinationGuardProps = {
  children: React.ReactNode;
  fallbackPath?: string;
};

export const DestinationGuard: React.FC<DestinationGuardProps> = ({
  children,
  fallbackPath = '/onboarding/destinations',
}) => {
  const location = useLocation();
  const { data: destinations, isLoading, error } = useDestinations();

  // Don't guard the onboarding routes themselves
  if (location.pathname.startsWith('/onboarding')) {
    return <>{children}</>;
  }

  // Loading state
  if (isLoading) {
    return (
      <Box
        display="flex"
        justifyContent="center"
        alignItems="center"
        minHeight="50vh"
        role="status"
        aria-label="Loading destinations"
      >
        <CircularProgress aria-label="Loading destinations" size={48} />
      </Box>
    );
  }

  // Error state
  if (error) {
    return (
      <Box p={3}>
        <Alert severity="error" role="alert" aria-live="polite">
          Failed to load destinations. Please refresh the page or contact support.
        </Alert>
      </Box>
    );
  }

  // No destinations - redirect to onboarding
  if (!destinations || destinations.length === 0) {
    return <Navigate to={fallbackPath} replace state={{ from: location.pathname }} />;
  }

  // Has destinations - allow access
  return <>{children}</>;
};
