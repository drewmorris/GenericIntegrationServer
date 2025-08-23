/**
 * Connector Setup Complete Component
 * Placeholder for setup completion
 */

import { Box, Typography } from '@mui/material';
import type React from 'react';

export type ConnectorSetupCompleteProps = {
  onDataChange: (data: any) => void;
};

export const ConnectorSetupComplete: React.FC<ConnectorSetupCompleteProps> = ({
  onDataChange: _onDataChange,
}) => {
  return (
    <Box>
      <Typography variant="h6">Setup Complete</Typography>
      <Typography variant="body2" color="text.secondary">
        Your connector has been successfully configured.
      </Typography>
    </Box>
  );
};
