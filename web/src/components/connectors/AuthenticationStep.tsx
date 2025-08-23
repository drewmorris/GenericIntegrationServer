/**
 * Authentication Step Component
 * Placeholder for connector authentication
 */

import { Box, Typography } from '@mui/material';
import type React from 'react';

export type AuthenticationStepProps = {
  onDataChange: (data: any) => void;
};

export const AuthenticationStep: React.FC<AuthenticationStepProps> = ({
  onDataChange: _onDataChange,
}) => {
  return (
    <Box>
      <Typography variant="h6">Authentication</Typography>
      <Typography variant="body2" color="text.secondary">
        Set up authentication for your connector.
      </Typography>
    </Box>
  );
};
