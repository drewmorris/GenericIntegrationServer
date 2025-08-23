/**
 * Destination Selector Component
 * Visual gallery for selecting destination type during onboarding
 * Follows Material Design card patterns with accessibility support
 */

import {
  Star as StarIcon,
  TrendingUp as TrendingUpIcon,
  Verified as VerifiedIcon,
} from '@mui/icons-material';
import {
  Alert,
  Avatar,
  Badge,
  Box,
  Card,
  CardActionArea,
  CardContent,
  Chip,
  Grid,
  Skeleton,
  Typography,
} from '@mui/material';
import type React from 'react';
import { useEffect, useId, useState } from 'react';
import { getDestinationLogo } from '../../assets/connector-logos';
import { useDestinationDefinitions } from '../../hooks/useDestinationDefinitions';

type DestinationDefinition = {
  name: string;
  displayName?: string;
  description?: string;
  [key: string]: any;
};

const getDifficultyColor = (difficulty: string) => {
  switch (difficulty) {
    case 'Easy': {
      return 'success';
    }
    case 'Medium': {
      return 'warning';
    }
    case 'Advanced': {
      return 'error';
    }
    default: {
      return 'default';
    }
  }
};

type DestinationSelectorProps = {
  wizardData: Record<string, any>;
  onDataChange: (data: any) => void;
};

type DestinationOption = {
  name: string;
  displayName: string;
  description: string;
  features: string[];
  difficulty: 'Easy' | 'Medium' | 'Advanced';
  popular?: boolean;
  recommended?: boolean;
  enterprise?: boolean;
};

// Destination metadata for better UX
const destinationMetadata: Record<string, DestinationOption> = {
  cleverbrag: {
    name: 'cleverbrag',
    displayName: 'CleverBrag',
    description:
      'AI-powered knowledge management and retrieval system with advanced search capabilities',
    features: ['AI Search', 'Knowledge Management', 'Real-time Indexing', 'Multi-format Support'],
    difficulty: 'Easy',
    popular: true,
    recommended: true,
  },
  onyx: {
    name: 'onyx',
    displayName: 'Onyx',
    description: 'Open-source enterprise search and knowledge management platform',
    features: ['Enterprise Search', 'Document Processing', 'User Management', 'Analytics'],
    difficulty: 'Medium',
    enterprise: true,
  },
  csv: {
    name: 'csv',
    displayName: 'CSV Export',
    description: 'Export your data to CSV files for analysis and reporting',
    features: ['Data Export', 'Custom Formatting', 'Scheduled Exports', 'Easy Integration'],
    difficulty: 'Easy',
  },
};

export const DestinationSelector: React.FC<DestinationSelectorProps> = ({
  wizardData,
  onDataChange,
}) => {
  const [selectedDestination, setSelectedDestination] = useState<string | null>(
    wizardData.destinationType || null,
  );

  // Generate unique ID
  const destinationSelectorHeadingId = useId();

  const { data: definitionsData, isLoading, error } = useDestinationDefinitions();
  const definitions: DestinationDefinition[] = Array.isArray(definitionsData)
    ? definitionsData
    : [];

  useEffect(() => {
    if (selectedDestination) {
      onDataChange({
        destinationType: selectedDestination,
        destinationMetadata: destinationMetadata[selectedDestination],
      });
    }
  }, [selectedDestination, onDataChange]);

  const handleDestinationSelect = (destinationName: string) => {
    setSelectedDestination(destinationName);
  };

  const handleKeyDown = (event: React.KeyboardEvent, destinationName: string) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      handleDestinationSelect(destinationName);
    }
  };

  if (isLoading) {
    return <DestinationSelectorLoading />;
  }

  if (error) {
    return (
      <Alert severity="error" role="alert">
        Failed to load available destinations. Please refresh the page or contact support.
      </Alert>
    );
  }

  if (!definitions || definitions.length === 0) {
    return (
      <Alert severity="warning" role="alert">
        No destinations are currently available. Please contact your administrator.
      </Alert>
    );
  }

  return (
    <Box role="region" aria-labelledby={destinationSelectorHeadingId}>
      <Typography
        id={destinationSelectorHeadingId}
        variant="h5"
        component="h2"
        gutterBottom
        sx={{ mb: 3 }}
      >
        Choose Your Destination
      </Typography>

      <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
        Select where you want to send your synchronized data. You can add more destinations later.
      </Typography>

      <Grid container spacing={3}>
        {definitions.map((definition) => {
          const metadata = destinationMetadata[definition.name] || {
            name: definition.name,
            displayName: definition.name,
            description: 'Custom destination connector',
            features: ['Data Sync'],
            difficulty: 'Medium' as const,
          };

          const isSelected = selectedDestination === definition.name;

          return (
            <Grid item xs={12} sm={6} md={4} key={definition.name}>
              <DestinationCard
                definition={definition}
                metadata={metadata}
                isSelected={isSelected}
                onSelect={() => handleDestinationSelect(definition.name)}
                onKeyDown={(e) => handleKeyDown(e, definition.name)}
              />
            </Grid>
          );
        })}
      </Grid>

      {selectedDestination && (
        <Box sx={{ mt: 4 }}>
          <Alert severity="success" role="status" aria-live="polite">
            <Typography variant="body2">
              <strong>{destinationMetadata[selectedDestination]?.displayName}</strong> selected.
              Click "Continue" to configure the connection.
            </Typography>
          </Alert>
        </Box>
      )}
    </Box>
  );
};

type DestinationCardProps = {
  definition: any;
  metadata: DestinationOption;
  isSelected: boolean;
  onSelect: () => void;
  onKeyDown: (event: React.KeyboardEvent) => void;
};

const DestinationCard: React.FC<DestinationCardProps> = ({
  definition: _definition,
  metadata,
  isSelected,
  onSelect,
  onKeyDown,
}) => {
  const [isHovered, setIsHovered] = useState(false);
  const [isFocused, setIsFocused] = useState(false);

  return (
    <Card
      sx={{
        height: '100%',
        transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
        transform: isHovered || isFocused || isSelected ? 'translateY(-2px)' : 'translateY(0)',
        boxShadow: isHovered || isFocused ? 4 : isSelected ? 3 : 1,
        border: '2px solid',
        borderColor: isSelected ? 'primary.main' : 'transparent',
        position: 'relative',
      }}
    >
      {/* Badges */}
      {(metadata.recommended || metadata.popular || metadata.enterprise) && (
        <Box sx={{ position: 'absolute', top: 8, right: 8, zIndex: 1 }}>
          {metadata.recommended && (
            <Badge
              badgeContent={<VerifiedIcon sx={{ fontSize: 12 }} />}
              color="primary"
              sx={{ mr: 0.5 }}
              aria-label="Recommended destination"
            />
          )}
          {metadata.popular && (
            <Badge
              badgeContent={<StarIcon sx={{ fontSize: 12 }} />}
              color="secondary"
              sx={{ mr: 0.5 }}
              aria-label="Popular destination"
            />
          )}
          {metadata.enterprise && (
            <Badge
              badgeContent={<TrendingUpIcon sx={{ fontSize: 12 }} />}
              color="info"
              aria-label="Enterprise destination"
            />
          )}
        </Box>
      )}

      <CardActionArea
        onClick={onSelect}
        onKeyDown={onKeyDown}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
        onFocus={() => setIsFocused(true)}
        onBlur={() => setIsFocused(false)}
        sx={{
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'stretch',
          p: 0,
        }}
        aria-label={`Select ${metadata.displayName} destination`}
        aria-describedby={`destination-description-${metadata.name}`}
        aria-pressed={isSelected}
        role="button"
      >
        <CardContent
          sx={{
            height: '100%',
            display: 'flex',
            flexDirection: 'column',
            p: 3,
          }}
        >
          {/* Logo and Title */}
          <Box display="flex" alignItems="center" gap={2} mb={2}>
            <Avatar
              src={getDestinationLogo(metadata.name)}
              alt={`${metadata.displayName} logo`}
              sx={{
                width: 48,
                height: 48,
                border: '2px solid',
                borderColor: 'divider',
                bgcolor: 'background.paper',
              }}
            />
            <Box flex={1}>
              <Typography
                variant="h6"
                component="h3"
                sx={{
                  fontWeight: 600,
                  lineHeight: 1.2,
                }}
              >
                {metadata.displayName}
              </Typography>
              <Chip
                label={metadata.difficulty}
                size="small"
                color={getDifficultyColor(metadata.difficulty) as any}
                variant="outlined"
                sx={{ mt: 0.5 }}
              />
            </Box>
          </Box>

          {/* Description */}
          <Typography
            id={`destination-description-${metadata.name}`}
            variant="body2"
            color="text.secondary"
            sx={{
              flexGrow: 1,
              mb: 2,
              lineHeight: 1.5,
              display: '-webkit-box',
              WebkitLineClamp: 3,
              WebkitBoxOrient: 'vertical',
              overflow: 'hidden',
            }}
          >
            {metadata.description}
          </Typography>

          {/* Features */}
          <Box>
            <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display: 'block' }}>
              Key Features:
            </Typography>
            <Box display="flex" flexWrap="wrap" gap={0.5}>
              {metadata.features.slice(0, 3).map((feature) => (
                <Chip
                  key={feature}
                  label={feature}
                  size="small"
                  variant="outlined"
                  sx={{
                    fontSize: '0.7rem',
                    height: 24,
                  }}
                />
              ))}
              {metadata.features.length > 3 && (
                <Chip
                  label={`+${metadata.features.length - 3} more`}
                  size="small"
                  variant="outlined"
                  sx={{
                    fontSize: '0.7rem',
                    height: 24,
                  }}
                />
              )}
            </Box>
          </Box>

          {/* Selection Indicator */}
          {isSelected && (
            <Box
              sx={{
                position: 'absolute',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                bgcolor: 'primary.main',
                opacity: 0.1,
                pointerEvents: 'none',
              }}
            />
          )}
        </CardContent>
      </CardActionArea>
    </Card>
  );
};

// Loading component
const DestinationSelectorLoading: React.FC = () => (
  <Box>
    <Skeleton variant="text" width={300} height={40} sx={{ mb: 2 }} />
    <Skeleton variant="text" width="100%" height={24} sx={{ mb: 4 }} />

    <Grid container spacing={3}>
      {Array.from({ length: 3 }, (_, index) => ({
        id: `dest-selector-skeleton-${Date.now()}-${index}`,
      })).map((item) => (
        <Grid item xs={12} sm={6} md={4} key={item.id}>
          <Card sx={{ height: 280 }}>
            <CardContent sx={{ p: 3 }}>
              <Box display="flex" alignItems="center" gap={2} mb={2}>
                <Skeleton variant="circular" width={48} height={48} />
                <Box flex={1}>
                  <Skeleton variant="text" width="80%" height={28} />
                  <Skeleton
                    variant="rectangular"
                    width={60}
                    height={24}
                    sx={{ borderRadius: 12, mt: 0.5 }}
                  />
                </Box>
              </Box>
              <Skeleton variant="text" width="100%" height={20} sx={{ mb: 1 }} />
              <Skeleton variant="text" width="100%" height={20} sx={{ mb: 1 }} />
              <Skeleton variant="text" width="60%" height={20} sx={{ mb: 2 }} />
              <Box display="flex" gap={0.5} flexWrap="wrap">
                <Skeleton variant="rectangular" width={60} height={24} sx={{ borderRadius: 12 }} />
                <Skeleton variant="rectangular" width={80} height={24} sx={{ borderRadius: 12 }} />
                <Skeleton variant="rectangular" width={70} height={24} sx={{ borderRadius: 12 }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>
      ))}
    </Grid>
  </Box>
);
