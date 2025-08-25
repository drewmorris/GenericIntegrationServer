/**
 * AuthLoadingSpinner - Loading screen during authentication state changes
 * Prevents blank screens during token refresh or auth transitions
 */

import { Security as SecurityIcon } from '@mui/icons-material';
import { Box, CircularProgress, LinearProgress, Typography } from '@mui/material';

interface AuthLoadingSpinnerProps {
  message?: string;
  showProgress?: boolean;
}

export const AuthLoadingSpinner: React.FC<AuthLoadingSpinnerProps> = ({
  message = 'Authenticating...',
  showProgress = false,
}) => {
  return (
    <Box
      display="flex"
      flexDirection="column"
      justifyContent="center"
      alignItems="center"
      minHeight="100vh"
      bgcolor="background.default"
      sx={{
        background: 'linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)',
      }}
    >
      <Box
        display="flex"
        flexDirection="column"
        alignItems="center"
        p={4}
        borderRadius={2}
        bgcolor="background.paper"
        boxShadow={3}
        minWidth={300}
      >
        <SecurityIcon
          sx={{
            fontSize: 48,
            color: 'primary.main',
            mb: 2,
          }}
        />

        <Typography variant="h6" gutterBottom>
          Integration Server
        </Typography>

        <Typography variant="body2" color="text.secondary" gutterBottom>
          {message}
        </Typography>

        <Box sx={{ mt: 2, width: '100%' }}>
          {showProgress ? (
            <LinearProgress />
          ) : (
            <Box display="flex" justifyContent="center">
              <CircularProgress size={32} />
            </Box>
          )}
        </Box>

        <Typography variant="caption" color="text.secondary" sx={{ mt: 2 }}>
          Please wait while we verify your credentials
        </Typography>
      </Box>
    </Box>
  );
};
