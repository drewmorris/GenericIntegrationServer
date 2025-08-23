/**
 * Sync Settings Step Component
 * Placeholder for sync configuration
 */

import { Box, Typography } from '@mui/material';
import type React from 'react';

export type SyncSettingsStepProps = {
  onDataChange: (data: any) => void;
};

export const SyncSettingsStep: React.FC<SyncSettingsStepProps> = ({
  onDataChange: _onDataChange,
}) => {
  return (
    <Box>
      <Typography variant="h6">Sync Settings</Typography>
      <Typography variant="body2" color="text.secondary">
        Configure how your data will be synchronized.
      </Typography>
    </Box>
  );
};
