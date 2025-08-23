import {
  Add as AddIcon,
  ArrowForward as ArrowForwardIcon,
  Search as SearchIcon,
} from '@mui/icons-material';
import {
  Alert,
  Avatar,
  Box,
  Button,
  Card,
  CardActionArea,
  CardContent,
  Chip,
  Grid,
  InputAdornment,
  Skeleton,
  Tab,
  Tabs,
  TextField,
  Typography,
} from '@mui/material';
import React, { useId, useMemo, useState } from 'react';

import {
  connectorCategories,
  getConnectorCategory,
  getConnectorLogo,
  getDestinationLogo,
} from '../assets/connector-logos';
import { useConnectorDefinitions } from '../hooks/useConnectorDefinitions';
import { useDestinations } from '../hooks/useDestinations';

// Constants
const PRIMARY_COLOR = 'primary.main';

type ConnectorDestinationPair = {
  connector: {
    source: string;
    name: string;
    description: string;
    auth_type: string;
  };
  destination: {
    id: string;
    name: string;
    config: Record<string, any>;
  };
  pairName: string;
  category: string;
};

type ConnectorGalleryProps = {
  onSelectPair: (pair: ConnectorDestinationPair) => void;
};

export const ConnectorGallery: React.FC<ConnectorGalleryProps> = ({ onSelectPair }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('All');
  const noDestinationsHeadingId = useId();
  const connectorGalleryHeadingId = useId();
  const searchHelpTextId = useId();

  const {
    data: connectors = [],
    isLoading: connectorsLoading,
    error: connectorsError,
  } = useConnectorDefinitions();
  const {
    data: destinations = [],
    isLoading: destinationsLoading,
    error: destinationsError,
  } = useDestinations();

  // Create connector-destination pairs
  const pairs = useMemo(() => {
    return connectors.flatMap((connector) =>
      destinations.map((destination) => ({
        connector,
        destination,
        pairName: `${connector.name} → ${destination.name}`,
        category: getConnectorCategory(connector.source),
      })),
    );
  }, [connectors, destinations]);

  // Filter pairs based on search and category
  const filteredPairs = useMemo(() => {
    return pairs.filter((pair) => {
      const matchesSearch =
        pair.pairName.toLowerCase().includes(searchTerm.toLowerCase()) ||
        pair.connector.description.toLowerCase().includes(searchTerm.toLowerCase());
      const matchesCategory = selectedCategory === 'All' || pair.category === selectedCategory;
      return matchesSearch && matchesCategory;
    });
  }, [pairs, searchTerm, selectedCategory]);

  const categories = ['All', ...Object.keys(connectorCategories)];

  // Loading state
  if (connectorsLoading || destinationsLoading) {
    return <ConnectorGalleryLoading />;
  }

  // Error state
  if (connectorsError || destinationsError) {
    return (
      <Alert severity="error" sx={{ mb: 3 }}>
        Failed to load connectors or destinations. Please try again.
      </Alert>
    );
  }

  // No destinations state - redirect to onboarding
  if (destinations.length === 0) {
    return (
      <Box textAlign="center" py={8} role="main" aria-labelledby={noDestinationsHeadingId}>
        <Typography id={noDestinationsHeadingId} variant="h5" gutterBottom component="h1">
          No Destinations Configured
        </Typography>
        <Typography variant="body1" color="text.secondary" mb={3}>
          You need to set up at least one destination before adding connectors.
        </Typography>
        <Button
          variant="contained"
          href="/onboarding/destinations"
          aria-describedby={noDestinationsHeadingId}
        >
          Set Up Your First Destination
        </Button>
      </Box>
    );
  }

  return (
    <Box role="main" aria-labelledby={connectorGalleryHeadingId}>
      {/* Header */}
      <Box mb={4}>
        <Typography id={connectorGalleryHeadingId} variant="h4" gutterBottom component="h1">
          Add Connector
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Choose a connector and destination pair to start syncing your data.
        </Typography>
      </Box>

      {/* Search and Filters */}
      <Box mb={4} role="search" aria-label="Filter connectors">
        <TextField
          fullWidth
          placeholder="Search connectors..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon aria-hidden="true" />
              </InputAdornment>
            ),
          }}
          sx={{ mb: 3 }}
          aria-label="Search connectors by name or description"
          inputProps={{
            'aria-describedby': searchHelpTextId,
          }}
        />
        <Typography id={searchHelpTextId} variant="srOnly" component="div">
          Type to filter connectors by name or description
        </Typography>

        <Tabs
          value={selectedCategory}
          onChange={(_, newValue) => setSelectedCategory(newValue)}
          variant="scrollable"
          scrollButtons="auto"
          aria-label="Filter connectors by category"
          sx={{
            '& .MuiTabs-scrollButtons': {
              '&.Mui-disabled': {
                opacity: 0.3,
              },
            },
          }}
        >
          {categories.map((category) => (
            <Tab
              key={category}
              label={category}
              value={category}
              aria-controls={`category-panel-${category}`}
              id={`category-tab-${category}`}
            />
          ))}
        </Tabs>
      </Box>

      {/* Connector Grid */}
      <Grid container spacing={3}>
        {filteredPairs.map((pair, _index) => (
          <Grid
            item
            xs={12}
            sm={6}
            md={4}
            lg={3}
            key={`${pair.connector.source}-${pair.destination.id}`}
          >
            <ConnectorPairCard pair={pair} onClick={() => onSelectPair(pair)} />
          </Grid>
        ))}
      </Grid>

      {filteredPairs.length === 0 && (
        <Box textAlign="center" py={8}>
          <Typography variant="h6" gutterBottom>
            No connectors found
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Try adjusting your search or category filter.
          </Typography>
        </Box>
      )}
    </Box>
  );
};

type ConnectorPairCardProps = {
  pair: ConnectorDestinationPair;
  onClick: () => void;
};

const ConnectorPairCard: React.FC<ConnectorPairCardProps> = ({ pair, onClick }) => {
  const [isHovered, setIsHovered] = useState(false);
  const [isFocused, setIsFocused] = useState(false);

  const handleKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      onClick();
    }
  };

  return (
    <Card
      sx={{
        height: '100%',
        transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)', // Material Design easing
        transform: isHovered || isFocused ? 'translateY(-2px)' : 'translateY(0)',
        boxShadow: isHovered || isFocused ? 4 : 1, // Material Design elevation
        border: '1px solid',
        borderColor: isFocused ? PRIMARY_COLOR : 'divider',
        borderWidth: isFocused ? 2 : 1,
        '&:hover': {
          boxShadow: 4,
        },
        '&:focus-within': {
          boxShadow: 4,
          borderColor: PRIMARY_COLOR,
          borderWidth: 2,
        },
      }}
    >
      <CardActionArea
        onClick={onClick}
        onKeyDown={handleKeyDown}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
        onFocus={() => setIsFocused(true)}
        onBlur={() => setIsFocused(false)}
        sx={{
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'stretch',
          minHeight: 200, // Ensure consistent card height
        }}
        aria-label={`Add ${pair.pairName} connector`}
        aria-describedby={`card-description-${pair.connector.source}-${pair.destination.id}`}
      >
        <CardContent sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
          {/* Logo Flow */}
          <Box display="flex" alignItems="center" justifyContent="center" gap={1.5} mb={2} py={2}>
            <Avatar
              src={getConnectorLogo(pair.connector.source)}
              alt={pair.connector.name}
              sx={{
                width: 48,
                height: 48,
                border: '2px solid',
                borderColor: PRIMARY_COLOR,
                bgcolor: 'background.paper',
              }}
            />
            <ArrowForwardIcon
              color="primary"
              sx={{
                fontSize: 24,
                transition: 'transform 0.2s ease-in-out',
                transform: isHovered ? 'translateX(4px)' : 'translateX(0)',
              }}
            />
            <Avatar
              src={getDestinationLogo(pair.destination.name)}
              alt={pair.destination.name}
              sx={{
                width: 48,
                height: 48,
                border: '2px solid',
                borderColor: 'secondary.main',
                bgcolor: 'background.paper',
              }}
            />
          </Box>

          {/* Pair Name */}
          <Typography
            variant="h6"
            gutterBottom
            textAlign="center"
            sx={{
              fontSize: '1rem',
              fontWeight: 600,
              lineHeight: 1.3,
            }}
          >
            {pair.pairName}
          </Typography>

          {/* Description */}
          <Typography
            id={`card-description-${pair.connector.source}-${pair.destination.id}`}
            variant="body2"
            color="text.secondary"
            textAlign="center"
            sx={{
              flexGrow: 1,
              mb: 2,
              fontSize: '0.875rem',
              lineHeight: 1.4,
            }}
          >
            {pair.connector.description}
          </Typography>

          {/* Tags */}
          <Box display="flex" gap={1} flexWrap="wrap" justifyContent="center">
            <Chip
              label={pair.category}
              size="small"
              color="primary"
              variant="outlined"
              sx={{ fontSize: '0.75rem' }}
            />
            {pair.connector.auth_type === 'oauth' && (
              <Chip
                label="OAuth"
                size="small"
                color="success"
                variant="outlined"
                sx={{ fontSize: '0.75rem' }}
              />
            )}
          </Box>

          {/* Add Button Overlay */}
          <Box
            sx={{
              position: 'absolute',
              top: 8,
              right: 8,
              opacity: isHovered ? 1 : 0,
              transition: 'opacity 0.2s ease-in-out',
            }}
          >
            <Box
              sx={{
                bgcolor: PRIMARY_COLOR,
                color: 'primary.contrastText',
                borderRadius: '50%',
                width: 32,
                height: 32,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <AddIcon sx={{ fontSize: 18 }} />
            </Box>
          </Box>
        </CardContent>
      </CardActionArea>
    </Card>
  );
};

// Loading component for better UX
const ConnectorGalleryLoading: React.FC = () => (
  <Box role="main" aria-label="Loading connectors">
    <Box mb={4}>
      <Skeleton variant="text" width={200} height={48} />
      <Skeleton variant="text" width={400} height={24} />
    </Box>

    <Box mb={4}>
      <Skeleton variant="rectangular" width="100%" height={56} sx={{ mb: 3 }} />
      <Skeleton variant="rectangular" width="100%" height={48} />
    </Box>

    <Grid container spacing={3}>
      {Array.from({ length: 6 }, (_, index) => ({
        id: `connector-skeleton-${Date.now()}-${index}`,
      })).map((item, index) => (
        <Grid item xs={12} sm={6} md={4} lg={3} key={item.id}>
          <Card sx={{ height: 200 }}>
            <CardContent>
              <Box
                display="flex"
                alignItems="center"
                justifyContent="center"
                gap={1.5}
                mb={2}
                py={2}
              >
                <Skeleton variant="circular" width={48} height={48} />
                <Skeleton variant="rectangular" width={24} height={24} />
                <Skeleton variant="circular" width={48} height={48} />
              </Box>
              <Skeleton variant="text" width="80%" height={24} sx={{ mx: 'auto', mb: 1 }} />
              <Skeleton variant="text" width="100%" height={20} sx={{ mb: 1 }} />
              <Skeleton variant="text" width="60%" height={20} sx={{ mx: 'auto', mb: 2 }} />
              <Box display="flex" gap={1} justifyContent="center">
                <Skeleton variant="rectangular" width={60} height={24} sx={{ borderRadius: 12 }} />
                <Skeleton variant="rectangular" width={50} height={24} sx={{ borderRadius: 12 }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>
      ))}
    </Grid>
  </Box>
);
