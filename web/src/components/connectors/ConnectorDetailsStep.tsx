/**
 * Connector Details Step Component
 * Placeholder for connector configuration wizard
 */

import { Box, Typography } from '@mui/material';
import type React from 'react';

export type ConnectorDetailsStepProps = {
  onDataChange: (data: any) => void;
};

export const ConnectorDetailsStep: React.FC<ConnectorDetailsStepProps> = ({
  onDataChange: _onDataChange,
}) => {
  return (
    <Box>
      <Typography variant="h6">Connector Details</Typography>
      <Typography variant="body2" color="text.secondary">
        Configure your connector details here.
      </Typography>
    </Box>
  );
};
