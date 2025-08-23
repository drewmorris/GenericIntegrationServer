/**
 * Destination Delete Dialog
 * Confirmation dialog for destination deletion with impact assessment
 * Provides clear warnings about consequences and safety measures
 */

import {
  Cancel as CancelIcon,
  Delete as DeleteIcon,
  Link as LinkIcon,
  Schedule as ScheduleIcon,
  Storage as StorageIcon,
  Warning as WarningIcon,
} from '@mui/icons-material';
import {
  Alert,
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  TextField,
  Typography,
} from '@mui/material';
import React, { useId, useState } from 'react';

const getSeverityColor = (severity: string) => {
  switch (severity) {
    case 'high': {
      return 'error';
    }
    case 'medium': {
      return 'warning';
    }
    case 'low': {
      return 'info';
    }
    default: {
      return 'default';
    }
  }
};

type DestinationDeleteDialogProps = {
  destination: {
    id: string;
    name: string;
    displayName?: string;
    status: string;
    connectorCount?: number;
    syncCount?: number;
  };
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
};

export const DestinationDeleteDialog: React.FC<DestinationDeleteDialogProps> = ({
  destination,
  open,
  onClose,
  onConfirm,
}) => {
  const [confirmationText, setConfirmationText] = useState('');
  const [isDeleting, setIsDeleting] = useState(false);

  // Generate unique ID
  const deleteDialogTitleId = useId();

  const destinationName = destination.displayName || destination.name;
  const expectedConfirmation = `delete ${destinationName}`;
  const isConfirmationValid = confirmationText.toLowerCase() === expectedConfirmation.toLowerCase();

  const handleConfirm = () => {
    if (!isConfirmationValid) return;

    setIsDeleting(true);
    try {
      void onConfirm();
    } finally {
      setIsDeleting(false);
    }
  };

  const impactItems = [
    {
      icon: LinkIcon,
      primary: `${destination.connectorCount || 0} connected connectors`,
      secondary: 'All connectors using this destination will be disabled',
      severity: destination.connectorCount ? 'high' : 'low',
    },
    {
      icon: StorageIcon,
      primary: `${destination.syncCount || 0} historical syncs`,
      secondary: 'Sync history and logs will be preserved but orphaned',
      severity: destination.syncCount ? 'medium' : 'low',
    },
    {
      icon: ScheduleIcon,
      primary: 'Scheduled sync jobs',
      secondary: 'All scheduled syncs for this destination will be cancelled',
      severity: destination.connectorCount ? 'high' : 'low',
    },
  ];

  const hasHighImpact = impactItems.some((item) => item.severity === 'high');

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="sm"
      fullWidth
      aria-labelledby={deleteDialogTitleId}
    >
      <DialogTitle>
        <Box display="flex" alignItems="center" gap={2}>
          <WarningIcon color="error" />
          <Typography variant="h6" component="h2" id={deleteDialogTitleId}>
            Delete Destination
          </Typography>
        </Box>
      </DialogTitle>

      <DialogContent>
        <Alert severity="error" sx={{ mb: 3 }}>
          <Typography variant="body2" sx={{ fontWeight: 600, mb: 1 }}>
            This action cannot be undone!
          </Typography>
          <Typography variant="body2">
            Deleting "{destinationName}" will permanently remove the destination and affect all
            connected connectors and sync jobs.
          </Typography>
        </Alert>

        {/* Impact Assessment */}
        <Typography variant="h6" gutterBottom>
          Impact Assessment
        </Typography>

        <List dense>
          {impactItems.map((item) => (
            <React.Fragment key={item.primary}>
              <ListItem>
                <ListItemIcon>
                  <item.icon color={getSeverityColor(item.severity) as any} />
                </ListItemIcon>
                <ListItemText
                  primary={
                    <Box display="flex" alignItems="center" gap={1}>
                      <Typography variant="body2">{item.primary}</Typography>
                      <Chip
                        label={item.severity}
                        size="small"
                        color={getSeverityColor(item.severity) as any}
                        variant="outlined"
                      />
                    </Box>
                  }
                  secondary={item.secondary}
                />
              </ListItem>
              {index < impactItems.length - 1 && <Divider />}
            </React.Fragment>
          ))}
        </List>

        {/* High Impact Warning */}
        {hasHighImpact && (
          <Alert severity="warning" sx={{ mt: 3, mb: 3 }}>
            <Typography variant="body2" sx={{ fontWeight: 600, mb: 1 }}>
              High Impact Deletion
            </Typography>
            <Typography variant="body2">
              This destination has active connectors. Consider disabling connectors first or
              migrating them to another destination before deletion.
            </Typography>
          </Alert>
        )}

        {/* Confirmation Input */}
        <Box sx={{ mt: 3 }}>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            To confirm deletion, please type: <strong>{expectedConfirmation}</strong>
          </Typography>

          <TextField
            fullWidth
            label="Confirmation"
            value={confirmationText}
            onChange={(e) => setConfirmationText(e.target.value)}
            placeholder={expectedConfirmation}
            error={confirmationText.length > 0 && !isConfirmationValid}
            helperText={
              confirmationText.length > 0 && !isConfirmationValid
                ? 'Confirmation text does not match'
                : 'Type the exact text above to enable deletion'
            }
            autoComplete="off"
            inputProps={{
              'aria-describedby': 'confirmation-help-text',
            }}
          />
        </Box>

        {/* Additional Warnings */}
        <Box sx={{ mt: 3 }}>
          <Typography variant="body2" color="text.secondary">
            <strong>What happens after deletion:</strong>
          </Typography>
          <ul style={{ margin: '8px 0', paddingLeft: 20 }}>
            <li>
              <Typography variant="body2" color="text.secondary">
                The destination configuration will be permanently removed
              </Typography>
            </li>
            <li>
              <Typography variant="body2" color="text.secondary">
                Connected connectors will be automatically disabled
              </Typography>
            </li>
            <li>
              <Typography variant="body2" color="text.secondary">
                Scheduled sync jobs will be cancelled
              </Typography>
            </li>
            <li>
              <Typography variant="body2" color="text.secondary">
                Historical sync data will remain but become orphaned
              </Typography>
            </li>
          </ul>
        </Box>
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose} disabled={isDeleting} startIcon={<CancelIcon />}>
          Cancel
        </Button>
        <Button
          variant="contained"
          color="error"
          onClick={handleConfirm}
          disabled={!isConfirmationValid || isDeleting}
          startIcon={<DeleteIcon />}
        >
          {isDeleting ? 'Deleting...' : 'Delete Destination'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};
