/**
 * Destination Card Component
 * Individual destination card with health status, actions, and usage metrics
 * Follows Material Design card patterns with comprehensive accessibility
 */

import {
  CheckCircle as CheckCircleIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
  Error as ErrorIcon,
  MoreVert as MoreVertIcon,
  Pause as PauseIcon,
  Schedule as ScheduleIcon,
  TrendingUp as TrendingUpIcon,
  Visibility as VisibilityIcon,
  Warning as WarningIcon,
} from '@mui/icons-material';
import {
  Avatar,
  Badge,
  Box,
  Card,
  CardActions,
  CardContent,
  Chip,
  Divider,
  IconButton,
  LinearProgress,
  Menu,
  MenuItem,
  Tooltip,
  Typography,
} from '@mui/material';
import { formatDistanceToNow } from 'date-fns';
import type React from 'react';
import { useState } from 'react';
import { getDestinationLogo } from '../../assets/connector-logos';
import { DestinationTarget } from '../../hooks/useDestinations';

// Constants
const ERROR_COLOR = 'error.main';

type DestinationCardProps = {
  destination: DestinationTarget;
  onHealthCheck: () => void;
  onEdit: () => void;
  onDelete: () => void;
};

export const DestinationCard: React.FC<DestinationCardProps> = ({
  destination,
  onHealthCheck,
  onEdit,
  onDelete,
}) => {
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [isHovered, setIsHovered] = useState(false);

  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    event.stopPropagation();
    setAnchorEl(event.currentTarget);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
  };

  const handleMenuAction = (action: () => void) => {
    action();
    handleMenuClose();
  };

  const getStatusIcon = () => {
    switch (destination.status) {
      case 'active': {
        return <CheckCircleIcon color="success" />;
      }
      case 'error': {
        return <ErrorIcon color="error" />;
      }
      case 'inactive': {
        return <PauseIcon color="disabled" />;
      }
      default: {
        return <WarningIcon color="warning" />;
      }
    }
  };

  const getStatusColor = () => {
    switch (destination.status) {
      case 'active': {
        return 'success';
      }
      case 'error': {
        return 'error';
      }
      case 'inactive': {
        return 'default';
      }
      default: {
        return 'warning';
      }
    }
  };

  const getHealthScore = () => {
    // Calculate health score based on error rate and recent activity
    const errorRate = destination.errorCount
      ? (destination.errorCount / (destination.syncCount || 1)) * 100
      : 0;

    if (destination.status === 'error') return 25;
    if (destination.status === 'inactive') return 50;
    if (errorRate > 10) return 60;
    if (errorRate > 5) return 80;
    return 95;
  };

  const healthScore = getHealthScore();

  return (
    <Card
      sx={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
        transform: isHovered ? 'translateY(-2px)' : 'translateY(0)',
        boxShadow: isHovered ? 4 : 1,
        '&:hover': {
          boxShadow: 4,
        },
      }}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      role="article"
      aria-labelledby={`destination-${destination.id}-title`}
    >
      <CardContent sx={{ flex: 1, pb: 1 }}>
        {/* Header */}
        <Box display="flex" alignItems="flex-start" gap={2} mb={2}>
          <Badge
            overlap="circular"
            anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
            badgeContent={getStatusIcon()}
          >
            <Avatar
              src={getDestinationLogo(destination.name)}
              alt={`${destination.displayName || destination.name} logo`}
              sx={{
                width: 56,
                height: 56,
                border: '2px solid',
                borderColor: 'divider',
                bgcolor: 'background.paper',
              }}
            />
          </Badge>

          <Box flex={1} minWidth={0}>
            <Typography
              id={`destination-${destination.id}-title`}
              variant="h6"
              component="h3"
              noWrap
              sx={{ fontWeight: 600 }}
            >
              {destination.displayName || destination.name}
            </Typography>

            <Box display="flex" alignItems="center" gap={1} mt={0.5}>
              <Chip
                label={destination.status}
                size="small"
                color={getStatusColor() as any}
                variant="outlined"
              />
              {destination.connectorCount !== undefined && (
                <Chip
                  label={`${destination.connectorCount} connectors`}
                  size="small"
                  variant="outlined"
                />
              )}
            </Box>
          </Box>

          <IconButton
            onClick={handleMenuOpen}
            size="small"
            aria-label={`More actions for ${destination.displayName || destination.name}`}
            aria-haspopup="true"
            aria-expanded={Boolean(anchorEl)}
          >
            <MoreVertIcon />
          </IconButton>
        </Box>

        {/* Health Score */}
        <Box mb={2}>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
            <Typography variant="body2" color="text.secondary">
              Health Score
            </Typography>
            <Typography
              variant="body2"
              color={
                healthScore >= 80
                  ? 'success.main'
                  : healthScore >= 60
                    ? 'warning.main'
                    : ERROR_COLOR
              }
              fontWeight={600}
            >
              {healthScore}%
            </Typography>
          </Box>
          <LinearProgress
            variant="determinate"
            value={healthScore}
            sx={{
              height: 6,
              borderRadius: 3,
              bgcolor: 'grey.200',
              '& .MuiLinearProgress-bar': {
                bgcolor:
                  healthScore >= 80
                    ? 'success.main'
                    : healthScore >= 60
                      ? 'warning.main'
                      : ERROR_COLOR,
                borderRadius: 3,
              },
            }}
            aria-label={`Health score: ${healthScore}%`}
          />
        </Box>

        {/* Metrics */}
        <Box display="flex" justifyContent="space-between" mb={2}>
          <Box textAlign="center" flex={1}>
            <Typography variant="h6" color="primary">
              {destination.syncCount || 0}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Syncs
            </Typography>
          </Box>

          <Divider orientation="vertical" flexItem />

          <Box textAlign="center" flex={1}>
            <Typography variant="h6" color={destination.errorCount ? ERROR_COLOR : 'text.primary'}>
              {destination.errorCount || 0}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Errors
            </Typography>
          </Box>

          <Divider orientation="vertical" flexItem />

          <Box textAlign="center" flex={1}>
            <Typography variant="h6" color="text.primary">
              {destination.connectorCount || 0}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Active
            </Typography>
          </Box>
        </Box>

        {/* Last Activity */}
        <Box display="flex" alignItems="center" gap={1}>
          <ScheduleIcon sx={{ fontSize: 16, color: 'text.secondary' }} />
          <Typography variant="caption" color="text.secondary">
            {destination.lastSync
              ? `Last sync ${formatDistanceToNow(new Date(destination.lastSync), { addSuffix: true })}`
              : destination.createdAt || destination.created_at
                ? `Created ${formatDistanceToNow(new Date(destination.createdAt || destination.created_at!), { addSuffix: true })}`
                : 'Creation date unknown'}
          </Typography>
        </Box>
      </CardContent>

      <CardActions sx={{ px: 2, pb: 2 }}>
        <Tooltip title="View health details">
          <IconButton onClick={onHealthCheck} size="small" aria-label="View destination health">
            <TrendingUpIcon />
          </IconButton>
        </Tooltip>

        <Tooltip title="Edit configuration">
          <IconButton onClick={onEdit} size="small" aria-label="Edit destination">
            <EditIcon />
          </IconButton>
        </Tooltip>

        <Box flex={1} />

        <Typography variant="caption" color="text.secondary">
          {destination.updatedAt || destination.updated_at
            ? `Updated ${formatDistanceToNow(new Date(destination.updatedAt || destination.updated_at!), { addSuffix: true })}`
            : 'Update date unknown'}
        </Typography>
      </CardActions>

      {/* Action Menu */}
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleMenuClose}
        anchorOrigin={{
          vertical: 'top',
          horizontal: 'right',
        }}
        transformOrigin={{
          vertical: 'top',
          horizontal: 'right',
        }}
      >
        <MenuItem onClick={() => handleMenuAction(onHealthCheck)}>
          <VisibilityIcon sx={{ mr: 1 }} />
          View Health
        </MenuItem>
        <MenuItem onClick={() => handleMenuAction(onEdit)}>
          <EditIcon sx={{ mr: 1 }} />
          Edit Configuration
        </MenuItem>
        <MenuItem onClick={() => handleMenuAction(onDelete)} sx={{ color: ERROR_COLOR }}>
          <DeleteIcon sx={{ mr: 1 }} />
          Delete Destination
        </MenuItem>
      </Menu>
    </Card>
  );
};
