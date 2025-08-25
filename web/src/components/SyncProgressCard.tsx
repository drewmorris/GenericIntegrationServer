/**
 * SyncProgressCard - Real-time sync progress display component
 * Shows progress bars, status indicators, and allows sync cancellation
 */

import {
  Cancel as CancelIcon,
  Error as ErrorIcon,
  PlayArrow as InProgressIcon,
  HourglassEmpty as PendingIcon,
  CheckCircle as SuccessIcon,
} from '@mui/icons-material';
import {
  Box,
  Card,
  CardContent,
  Chip,
  IconButton,
  LinearProgress,
  Stack,
  Tooltip,
  Typography,
} from '@mui/material';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import React from 'react';

import { api } from '../lib/api';
import type { IndexAttempt } from '../types';

interface SyncProgressCardProps {
  attempt: IndexAttempt;
  showCancelButton?: boolean;
  compact?: boolean;
}

const getStatusIcon = (status: IndexAttempt['status']) => {
  switch (status) {
    case 'SUCCESS':
      return <SuccessIcon color="success" />;
    case 'FAILED':
      return <ErrorIcon color="error" />;
    case 'IN_PROGRESS':
      return <InProgressIcon color="primary" />;
    case 'CANCELED':
      return <CancelIcon color="warning" />;
    default:
      return <PendingIcon color="disabled" />;
  }
};

const getStatusColor = (status: IndexAttempt['status']) => {
  switch (status) {
    case 'SUCCESS':
      return 'success';
    case 'FAILED':
      return 'error';
    case 'IN_PROGRESS':
      return 'primary';
    case 'CANCELED':
      return 'warning';
    default:
      return 'default';
  }
};

const calculateProgress = (attempt: IndexAttempt): number => {
  if (attempt.status === 'SUCCESS') return 100;
  if (attempt.status === 'FAILED' || attempt.status === 'CANCELED') return 0;

  if (attempt.total_batches && attempt.total_batches > 0) {
    return Math.min(100, (attempt.completed_batches / attempt.total_batches) * 100);
  }

  // Fallback to indeterminate progress if no batch info
  return 0;
};

const formatTimeAgo = (timestamp: string): string => {
  const now = new Date();
  const time = new Date(timestamp);
  const diffMs = now.getTime() - time.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffDays > 0) return `${diffDays}d ago`;
  if (diffHours > 0) return `${diffHours}h ago`;
  if (diffMins > 0) return `${diffMins}m ago`;
  return 'Just now';
};

export const SyncProgressCard: React.FC<SyncProgressCardProps> = ({
  attempt,
  showCancelButton = true,
  compact = false,
}) => {
  const queryClient = useQueryClient();
  const progress = calculateProgress(attempt);
  const isActive = attempt.status === 'IN_PROGRESS';

  const cancelMutation = useMutation({
    mutationFn: async () => {
      await api.post(`/cc-pairs/index-attempts/${attempt.id}/cancel`);
    },
    onSuccess: () => {
      // Invalidate queries to refresh the data
      queryClient.invalidateQueries({ queryKey: ['active-syncs'] });
    },
  });

  const handleCancel = () => {
    if (window.confirm('Are you sure you want to cancel this sync operation?')) {
      cancelMutation.mutate();
    }
  };

  return (
    <Card variant={compact ? 'outlined' : 'elevation'} sx={{ mb: compact ? 1 : 2 }}>
      <CardContent sx={{ pb: compact ? 1 : 2, '&:last-child': { pb: compact ? 1 : 2 } }}>
        <Stack spacing={compact ? 1 : 2}>
          {/* Header with status and cancel button */}
          <Box display="flex" justifyContent="space-between" alignItems="center">
            <Box display="flex" alignItems="center" gap={1}>
              {getStatusIcon(attempt.status)}
              <Typography variant={compact ? 'body2' : 'subtitle1'} fontWeight="medium">
                {attempt.connector_credential_pair?.name ||
                  `CC-Pair ${attempt.connector_credential_pair_id}`}
              </Typography>
              <Chip label={attempt.status} color={getStatusColor(attempt.status)} size="small" />
            </Box>

            {showCancelButton && isActive && !attempt.cancellation_requested && (
              <Tooltip title="Cancel sync">
                <IconButton
                  size="small"
                  color="error"
                  onClick={handleCancel}
                  disabled={cancelMutation.isPending}
                >
                  <CancelIcon fontSize="small" />
                </IconButton>
              </Tooltip>
            )}
          </Box>

          {/* Progress bar for active syncs */}
          {isActive && (
            <Box>
              <Box display="flex" justifyContent="space-between" alignItems="center" mb={0.5}>
                <Typography variant="caption" color="text.secondary">
                  Progress
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {attempt.total_batches
                    ? `${attempt.completed_batches}/${attempt.total_batches} batches`
                    : 'Processing...'}
                </Typography>
              </Box>
              <LinearProgress
                variant={attempt.total_batches ? 'determinate' : 'indeterminate'}
                value={progress}
                sx={{ height: 6, borderRadius: 1 }}
              />
            </Box>
          )}

          {/* Stats and timing info */}
          {!compact && (
            <Box display="flex" justifyContent="space-between" flexWrap="wrap" gap={2}>
              <Box>
                <Typography variant="caption" color="text.secondary" display="block">
                  Documents
                </Typography>
                <Typography variant="body2">
                  {attempt.new_docs_indexed.toLocaleString()} indexed
                </Typography>
              </Box>

              <Box>
                <Typography variant="caption" color="text.secondary" display="block">
                  Started
                </Typography>
                <Typography variant="body2">{formatTimeAgo(attempt.time_created)}</Typography>
              </Box>

              {attempt.last_heartbeat_time && isActive && (
                <Box>
                  <Typography variant="caption" color="text.secondary" display="block">
                    Last Activity
                  </Typography>
                  <Typography variant="body2">
                    {formatTimeAgo(attempt.last_heartbeat_time)}
                  </Typography>
                </Box>
              )}
            </Box>
          )}

          {/* Error message if failed */}
          {attempt.status === 'FAILED' && attempt.error_msg && (
            <Box sx={{ backgroundColor: 'error.lighter', p: 1, borderRadius: 1 }}>
              <Typography variant="caption" color="error.main" display="block">
                Error:
              </Typography>
              <Typography variant="body2" color="error.main">
                {attempt.error_msg}
              </Typography>
            </Box>
          )}

          {/* Cancellation requested indicator */}
          {attempt.cancellation_requested && (
            <Typography variant="caption" color="warning.main" fontStyle="italic">
              Cancellation requested - waiting for current batch to complete...
            </Typography>
          )}
        </Stack>
      </CardContent>
    </Card>
  );
};
