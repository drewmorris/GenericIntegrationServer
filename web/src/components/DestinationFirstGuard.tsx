/**
 * Destination-First Guard Component
 * Ensures users set up at least one destination before accessing connectors
 */

import { ArrowForward, Rocket } from '@mui/icons-material';
import { Alert, Box, Button, Paper, Typography } from '@mui/material';
import type React from 'react';
import { useLocation } from 'react-router-dom';
import { useDestinations } from '../hooks/useDestinations';

type DestinationFirstGuardProps = {
  children: React.ReactNode;
};

export default function DestinationFirstGuard({ children }: DestinationFirstGuardProps) {
  const { destinations, isLoading } = useDestinations();
  const location = useLocation();

  // Allow access to destination setup pages
  const allowedPaths = ['/destinations', '/destinations/setup', '/login', '/signup'];
  if (allowedPaths.some((path) => location.pathname.startsWith(path))) {
    return <>{children}</>;
  }

  if (isLoading) {
    return <div>Loading...</div>;
  }

  // If no destinations exist, show onboarding
  if (!destinations || destinations.length === 0) {
    return (
      <Box
        sx={{
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          bgcolor: 'grey.50',
        }}
      >
        <Paper
          sx={{
            p: 6,
            maxWidth: 600,
            textAlign: 'center',
            borderRadius: 3,
            boxShadow: 3,
          }}
        >
          <Rocket sx={{ fontSize: 80, color: 'primary.main', mb: 3 }} />

          <Typography variant="h4" gutterBottom fontWeight="bold">
            Welcome to Integration Server!
          </Typography>

          <Typography variant="h6" color="text.secondary" sx={{ mb: 4 }}>
            Let's get you started by setting up your first destination
          </Typography>

          <Alert severity="info" sx={{ mb: 4, textAlign: 'left' }}>
            <Typography variant="body2">
              <strong>Why destinations first?</strong>
              <br />
              Destinations are where your data goes (like CleverBrag, Onyx, or CSV files). You need
              at least one destination before you can sync data from connectors like Gmail, Slack,
              or Google Drive.
            </Typography>
          </Alert>

          <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center' }}>
            <Button
              variant="contained"
              size="large"
              endIcon={<ArrowForward />}
              onClick={() => {
                window.location.href = '/destinations/setup';
              }}
              sx={{ px: 4, py: 1.5 }}
            >
              Set Up Your First Destination
            </Button>
          </Box>

          <Typography variant="body2" color="text.secondary" sx={{ mt: 3 }}>
            This will only take 2-3 minutes
          </Typography>
        </Paper>
      </Box>
    );
  }

  // Destinations exist, allow normal access
  return <>{children}</>;
}
