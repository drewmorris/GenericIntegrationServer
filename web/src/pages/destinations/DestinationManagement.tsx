/**
 * Destination Management Page
 * Comprehensive interface for managing destinations with CRUD operations
 * Includes health monitoring, configuration updates, and usage analytics
 */

import { Add as AddIcon, Search as SearchIcon } from '@mui/icons-material';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Container,
  Fab,
  Grid,
  InputAdornment,
  TextField,
  Typography,
} from '@mui/material';
import React, { useId, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { DestinationCard } from '../../components/destinations/DestinationCard';
import { DestinationDeleteDialog } from '../../components/destinations/DestinationDeleteDialog';
import { DestinationEditDialog } from '../../components/destinations/DestinationEditDialog';
import { DestinationHealthDialog } from '../../components/destinations/DestinationHealthDialog';
import { useDeleteDestination } from '../../hooks/useDeleteDestination';
import { useDestinations } from '../../hooks/useDestinations';

// Constants
const SKELETON_COLOR = 'grey.200';

type FilterType = 'all' | 'active' | 'inactive' | 'error';
type SortType = 'name' | 'status' | 'created' | 'updated';

export const DestinationManagement: React.FC = () => {
  // Generate unique ID
  const destinationsHeadingId = useId();

  const navigate = useNavigate();
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState<FilterType>('all');
  const [sortType, setSortType] = useState<SortType>('name');
  const [selectedDestination, setSelectedDestination] = useState<any>(null);
  const [dialogType, setDialogType] = useState<'health' | 'edit' | 'delete' | null>(null);

  const { data: destinations = [], isLoading, error, refetch } = useDestinations();
  const { mutateAsync: deleteDestination } = useDeleteDestination();

  // Filter and sort destinations
  const filteredDestinations = useMemo(() => {
    const filtered = destinations.filter((dest) => {
      const matchesSearch =
        dest.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        dest.displayName?.toLowerCase().includes(searchTerm.toLowerCase());

      const matchesFilter = filterType === 'all' || dest.status === filterType;

      return matchesSearch && matchesFilter;
    });

    // Sort destinations
    filtered.sort((a, b) => {
      switch (sortType) {
        case 'name': {
          return (a.displayName || a.name).localeCompare(b.displayName || b.name);
        }
        case 'status': {
          return a.status.localeCompare(b.status);
        }
        case 'created': {
          return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime();
        }
        case 'updated': {
          return new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime();
        }
        default: {
          return 0;
        }
      }
    });

    return filtered;
  }, [destinations, searchTerm, filterType, sortType]);

  const handleAddDestination = () => {
    navigate('/onboarding/destinations');
  };

  const handleDestinationAction = (destination: any, action: 'health' | 'edit' | 'delete') => {
    setSelectedDestination(destination);
    setDialogType(action);
  };

  const handleCloseDialog = () => {
    setSelectedDestination(null);
    setDialogType(null);
  };

  const handleDeleteConfirm = async () => {
    if (selectedDestination) {
      await deleteDestination(selectedDestination.id);
      handleCloseDialog();
      void refetch();
    }
  };

  const getStatusCounts = () => {
    const counts = destinations.reduce(
      (acc, dest) => {
        acc[dest.status] = (acc[dest.status] || 0) + 1;
        return acc;
      },
      {} as Record<string, number>,
    );

    return {
      total: destinations.length,
      active: counts.active || 0,
      inactive: counts.inactive || 0,
      error: counts.error || 0,
    };
  };

  const statusCounts = getStatusCounts();

  if (error) {
    return (
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Alert
          severity="error"
          action={
            <Button color="inherit" size="small" onClick={() => refetch()}>
              Retry
            </Button>
          }
        >
          Failed to load destinations. Please try again.
        </Alert>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Box role="main" aria-labelledby="destinations-heading">
        {/* Header */}
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={4}>
          <Box>
            <Typography
              id={destinationsHeadingId}
              variant="h3"
              component="h1"
              gutterBottom
              sx={{ fontWeight: 300 }}
            >
              Destinations
            </Typography>
            <Typography variant="body1" color="text.secondary">
              Manage your data destinations and monitor their health
            </Typography>
          </Box>

          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={handleAddDestination}
            size="large"
            aria-label="Add new destination"
          >
            Add Destination
          </Button>
        </Box>

        {/* Status Overview */}
        <Grid container spacing={3} sx={{ mb: 4 }}>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent sx={{ textAlign: 'center', py: 3 }}>
                <Typography variant="h4" color="primary" gutterBottom>
                  {statusCounts.total}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Total Destinations
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent sx={{ textAlign: 'center', py: 3 }}>
                <Typography variant="h4" color="success.main" gutterBottom>
                  {statusCounts.active}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Active
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent sx={{ textAlign: 'center', py: 3 }}>
                <Typography variant="h4" color="warning.main" gutterBottom>
                  {statusCounts.inactive}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Inactive
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent sx={{ textAlign: 'center', py: 3 }}>
                <Typography variant="h4" color="error.main" gutterBottom>
                  {statusCounts.error}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Errors
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        {/* Search and Filters */}
        <Card sx={{ mb: 4 }}>
          <CardContent>
            <Grid container spacing={3} alignItems="center">
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  placeholder="Search destinations..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position="start">
                        <SearchIcon />
                      </InputAdornment>
                    ),
                  }}
                  aria-label="Search destinations by name"
                />
              </Grid>

              <Grid item xs={12} md={3}>
                <TextField
                  select
                  fullWidth
                  label="Filter by Status"
                  value={filterType}
                  onChange={(e) => setFilterType(e.target.value as FilterType)}
                  SelectProps={{
                    native: true,
                  }}
                >
                  <option value="all">All Statuses</option>
                  <option value="active">Active</option>
                  <option value="inactive">Inactive</option>
                  <option value="error">Error</option>
                </TextField>
              </Grid>

              <Grid item xs={12} md={3}>
                <TextField
                  select
                  fullWidth
                  label="Sort by"
                  value={sortType}
                  onChange={(e) => setSortType(e.target.value as SortType)}
                  SelectProps={{
                    native: true,
                  }}
                >
                  <option value="name">Name</option>
                  <option value="status">Status</option>
                  <option value="created">Date Created</option>
                  <option value="updated">Last Updated</option>
                </TextField>
              </Grid>
            </Grid>
          </CardContent>
        </Card>

        {/* Destinations Grid */}
        {isLoading ? (
          <DestinationManagementLoading />
        ) : filteredDestinations.length === 0 ? (
          <EmptyDestinationsState
            hasDestinations={destinations.length > 0}
            searchTerm={searchTerm}
            onAddDestination={handleAddDestination}
            onClearSearch={() => setSearchTerm('')}
          />
        ) : (
          <Grid container spacing={3}>
            {filteredDestinations.map((destination) => (
              <Grid item xs={12} sm={6} md={4} key={destination.id}>
                <DestinationCard
                  destination={destination}
                  onHealthCheck={() => handleDestinationAction(destination, 'health')}
                  onEdit={() => handleDestinationAction(destination, 'edit')}
                  onDelete={() => handleDestinationAction(destination, 'delete')}
                />
              </Grid>
            ))}
          </Grid>
        )}

        {/* Floating Action Button for Mobile */}
        <Fab
          color="primary"
          aria-label="Add destination"
          onClick={handleAddDestination}
          sx={{
            position: 'fixed',
            bottom: 16,
            right: 16,
            display: { xs: 'flex', md: 'none' },
          }}
        >
          <AddIcon />
        </Fab>

        {/* Dialogs */}
        {dialogType === 'health' && selectedDestination && (
          <DestinationHealthDialog
            destination={selectedDestination}
            open={true}
            onClose={handleCloseDialog}
          />
        )}

        {dialogType === 'edit' && selectedDestination && (
          <DestinationEditDialog
            destination={selectedDestination}
            open={true}
            onClose={handleCloseDialog}
            onSave={() => {
              handleCloseDialog();
              void refetch();
            }}
          />
        )}

        {dialogType === 'delete' && selectedDestination && (
          <DestinationDeleteDialog
            destination={selectedDestination}
            open={true}
            onClose={handleCloseDialog}
            onConfirm={handleDeleteConfirm}
          />
        )}
      </Box>
    </Container>
  );
};

// Loading component
const DestinationManagementLoading: React.FC = () => (
  <Grid container spacing={3}>
    {Array.from({ length: 6 }, (_, index) => ({
      id: `dest-mgmt-skeleton-${Date.now()}-${index}`,
    })).map((item) => (
      <Grid item xs={12} sm={6} md={4} key={item.id}>
        <Card sx={{ height: 280 }}>
          <CardContent>
            {/* Loading skeleton content */}
            <Box display="flex" alignItems="center" gap={2} mb={2}>
              <Box
                sx={{
                  width: 56,
                  height: 56,
                  borderRadius: '50%',
                  bgcolor: SKELETON_COLOR,
                  animation: 'pulse 1.5s ease-in-out infinite',
                }}
              />
              <Box flex={1}>
                <Box
                  sx={{
                    height: 24,
                    bgcolor: SKELETON_COLOR,
                    borderRadius: 1,
                    mb: 1,
                    animation: 'pulse 1.5s ease-in-out infinite',
                  }}
                />
                <Box
                  sx={{
                    height: 20,
                    width: '60%',
                    bgcolor: SKELETON_COLOR,
                    borderRadius: 1,
                    animation: 'pulse 1.5s ease-in-out infinite',
                  }}
                />
              </Box>
            </Box>
            <Box
              sx={{
                height: 16,
                bgcolor: SKELETON_COLOR,
                borderRadius: 1,
                mb: 1,
                animation: 'pulse 1.5s ease-in-out infinite',
              }}
            />
            <Box
              sx={{
                height: 16,
                width: '80%',
                bgcolor: SKELETON_COLOR,
                borderRadius: 1,
                animation: 'pulse 1.5s ease-in-out infinite',
              }}
            />
          </CardContent>
        </Card>
      </Grid>
    ))}
  </Grid>
);

// Empty state component
type EmptyDestinationsStateProps = {
  hasDestinations: boolean;
  searchTerm: string;
  onAddDestination: () => void;
  onClearSearch: () => void;
};

const EmptyDestinationsState: React.FC<EmptyDestinationsStateProps> = ({
  hasDestinations,
  searchTerm,
  onAddDestination,
  onClearSearch,
}) => {
  if (!hasDestinations) {
    // No destinations at all
    return (
      <Box textAlign="center" py={8}>
        <Typography variant="h5" gutterBottom>
          No Destinations Yet
        </Typography>
        <Typography variant="body1" color="text.secondary" mb={3}>
          Get started by adding your first destination where data will be sent.
        </Typography>
        <Button variant="contained" startIcon={<AddIcon />} onClick={onAddDestination} size="large">
          Add Your First Destination
        </Button>
      </Box>
    );
  }

  // Has destinations but search/filter returned empty
  return (
    <Box textAlign="center" py={8}>
      <Typography variant="h5" gutterBottom>
        No Destinations Found
      </Typography>
      <Typography variant="body1" color="text.secondary" mb={3}>
        {searchTerm
          ? `No destinations match "${searchTerm}". Try adjusting your search or filters.`
          : 'No destinations match your current filters.'}
      </Typography>
      <Box display="flex" gap={2} justifyContent="center">
        {searchTerm && (
          <Button variant="outlined" onClick={onClearSearch}>
            Clear Search
          </Button>
        )}
        <Button variant="contained" startIcon={<AddIcon />} onClick={onAddDestination}>
          Add Destination
        </Button>
      </Box>
    </Box>
  );
};
