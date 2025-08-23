/**
 * Connection Test Step Component
 * Placeholder for connection testing
 */

import { Box, Typography } from '@mui/material';
import type React from 'react';

export type ConnectionTestStepProps = {
  onDataChange: (data: any) => void;
};

export const ConnectionTestStep: React.FC<ConnectionTestStepProps> = ({
  onDataChange: _onDataChange,
}) => {
  return (
    <Box>
      <Typography variant="h6">Test Connection</Typography>
      <Typography variant="body2" color="text.secondary">
        Test your connector configuration.
      </Typography>
    </Box>
  );
};
