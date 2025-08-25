import {
  Add as AddIcon,
  CheckCircle as CheckIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
} from '@mui/icons-material';
import {
  Alert,
  Button,
  Card,
  CardActions,
  CardContent,
  CardHeader,
  Chip,
  Container,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  Divider,
  MenuItem,
  Paper,
  Select,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import { useSnackbar } from 'notistack';
import { useMemo, useState } from 'react';
import { useCreateDestinationTarget } from '../hooks/useCreateDestinationTarget';
import { useDeleteDestination } from '../hooks/useDeleteDestination';
import {
  type DestinationDefinition,
  useDestinationDefinitions,
} from '../hooks/useDestinationDefinitions';
import { type DestinationTarget, useDestinations } from '../hooks/useDestinations';
import { useUpdateDestinationTarget } from '../hooks/useUpdateDestination';

export default function DestinationsPage() {
  const { data, isLoading, error, refetch } = useDestinationDefinitions();
  const defs: DestinationDefinition[] = Array.isArray(data) ? data : [];
  const { destinations, isLoading: isLoadingDestinations } = useDestinations();
  const createDestinationMutation = useCreateDestinationTarget();
  const updateDestinationMutation = useUpdateDestinationTarget();
  const deleteDestinationMutation = useDeleteDestination();
  const { enqueueSnackbar } = useSnackbar();

  const [selected, setSelected] = useState<string>('');
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingDestination, setEditingDestination] = useState<DestinationTarget | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [destinationToDelete, setDestinationToDelete] = useState<DestinationTarget | null>(null);

  const def: DestinationDefinition | undefined = useMemo(
    () => (defs.length > 0 ? defs.find((d) => d.name === selected) || defs[0] : undefined),
    [defs, selected],
  );
  const [values, setValues] = useState<Record<string, string>>({});
  const [editValues, setEditValues] = useState<Record<string, string>>({});

  if (isLoading) {
    return (
      <Container maxWidth="md" sx={{ mt: 4 }}>
        <Typography variant="h5">Loading destinations…</Typography>
      </Container>
    );
  }
  if (error) {
    return (
      <Container maxWidth="md" sx={{ mt: 4 }}>
        <Alert severity="error" sx={{ mb: 2 }}>
          Failed to load destinations: {String(error.message)}
        </Alert>
        <Button variant="outlined" onClick={() => void refetch()}>
          Retry
        </Button>
      </Container>
    );
  }

  if (defs.length === 0) {
    return (
      <Container maxWidth="md" sx={{ mt: 4 }}>
        <Alert severity="info" sx={{ mb: 2 }}>
          No destinations found.
        </Alert>
        <Stack direction="row" spacing={2}>
          <Button variant="outlined" onClick={() => void refetch()}>
            Refresh
          </Button>
          <Button variant="contained" onClick={() => void refetch()}>
            Add Destination
          </Button>
        </Stack>
      </Container>
    );
  }

  const props = def?.schema?.properties ?? {};
  const req = new Set<string>(def?.schema?.required ?? []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!def) return;

    const payload = {
      name: def.name,
      display_name: def.schema?.title || def.name,
      config: values,
    };

    try {
      await createDestinationMutation.mutateAsync(payload);
      enqueueSnackbar(`${payload.display_name} destination created successfully!`, {
        variant: 'success',
        autoHideDuration: 4000,
      });

      // Reset form and hide it
      setValues({});
      setShowCreateForm(false);
    } catch (error: any) {
      console.error('Failed to save destination:', error);

      // Extract meaningful error message
      let errorMessage = 'Failed to save destination';
      if (error.response?.data?.detail) {
        errorMessage = error.response.data.detail;
      } else if (error.message) {
        errorMessage = error.message;
      }

      enqueueSnackbar(errorMessage, {
        variant: 'error',
        autoHideDuration: 6000,
      });
    }
  };

  const handleEditDestination = (destination: DestinationTarget) => {
    setEditingDestination(destination);
    // Pre-fill form with current config values
    const editDef = defs.find((d) => d.name === destination.name);
    const currentValues: Record<string, string> = {};
    if (editDef?.schema?.properties) {
      Object.keys(editDef.schema.properties).forEach((key) => {
        currentValues[key] = destination.config[key] || '';
      });
    }
    setEditValues(currentValues);
    setSelected(destination.name); // Set the type selector
  };

  const handleUpdateDestination = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingDestination) return;

    try {
      await updateDestinationMutation.mutateAsync({
        id: editingDestination.id,
        display_name: editingDestination.display_name,
        config: editValues,
      });

      enqueueSnackbar(`${editingDestination.display_name} updated successfully!`, {
        variant: 'success',
        autoHideDuration: 4000,
      });

      setEditingDestination(null);
      setEditValues({});
    } catch (error: any) {
      console.error('Failed to update destination:', error);

      let errorMessage = 'Failed to update destination';
      if (error.response?.data?.detail) {
        errorMessage = error.response.data.detail;
      } else if (error.message) {
        errorMessage = error.message;
      }

      enqueueSnackbar(errorMessage, {
        variant: 'error',
        autoHideDuration: 6000,
      });
    }
  };

  const handleDeleteDestination = (destination: DestinationTarget) => {
    setDestinationToDelete(destination);
    setDeleteDialogOpen(true);
  };

  const confirmDeleteDestination = async () => {
    if (!destinationToDelete) return;

    try {
      await deleteDestinationMutation.mutateAsync(destinationToDelete.id);

      enqueueSnackbar(`${destinationToDelete.display_name} deleted successfully!`, {
        variant: 'success',
        autoHideDuration: 4000,
      });

      setDeleteDialogOpen(false);
      setDestinationToDelete(null);
    } catch (error: any) {
      console.error('Failed to delete destination:', error);

      let errorMessage = 'Failed to delete destination';
      if (error.response?.data?.detail) {
        errorMessage = error.response.data.detail;
      } else if (error.message) {
        errorMessage = error.message;
      }

      enqueueSnackbar(errorMessage, {
        variant: 'error',
        autoHideDuration: 6000,
      });
    }
  };

  return (
    <Container maxWidth="lg" sx={{ mt: 4 }}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 3 }}>
        <Typography variant="h4">Destinations</Typography>
        {!showCreateForm && (
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => setShowCreateForm(true)}
            disabled={defs.length === 0}
          >
            Add Destination
          </Button>
        )}
      </Stack>

      {/* Existing Destinations */}
      {isLoadingDestinations ? (
        <Paper sx={{ p: 3, textAlign: 'center' }}>
          <Typography variant="body1">Loading saved destinations...</Typography>
        </Paper>
      ) : destinations.length > 0 ? (
        <Stack spacing={2} sx={{ mb: 4 }}>
          <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <CheckIcon color="success" />
            Configured Destinations ({destinations.length})
          </Typography>
          {destinations.map((destination) => (
            <Card key={destination.id} variant="outlined">
              <CardHeader
                title={destination.display_name}
                subheader={`Type: ${destination.name}`}
                action={<Chip label="Active" color="success" size="small" icon={<CheckIcon />} />}
              />
              <CardContent sx={{ pt: 0 }}>
                <Typography variant="body2" color="text.secondary">
                  Configuration includes {Object.keys(destination.config).length} settings
                </Typography>
              </CardContent>
              <CardActions>
                <Button
                  size="small"
                  startIcon={<EditIcon />}
                  onClick={() => handleEditDestination(destination)}
                >
                  Edit
                </Button>
                <Button
                  size="small"
                  color="error"
                  startIcon={<DeleteIcon />}
                  onClick={() => handleDeleteDestination(destination)}
                >
                  Delete
                </Button>
              </CardActions>
            </Card>
          ))}
        </Stack>
      ) : (
        <Paper sx={{ p: 3, textAlign: 'center', mb: 4 }}>
          <Typography variant="body1" color="text.secondary">
            No destinations configured yet. Add your first destination to get started.
          </Typography>
        </Paper>
      )}

      {/* Create New Destination Form */}
      {showCreateForm && (
        <>
          <Divider sx={{ my: 3 }} />
          <Paper sx={{ p: 3 }}>
            <Stack spacing={3}>
              <Stack direction="row" justifyContent="space-between" alignItems="center">
                <Typography variant="h6">Add New Destination</Typography>
                <Button
                  variant="outlined"
                  size="small"
                  onClick={() => {
                    setShowCreateForm(false);
                    setValues({});
                  }}
                >
                  Cancel
                </Button>
              </Stack>

              <Stack direction="row" spacing={2} alignItems="center">
                <Typography variant="body2" color="text.secondary">
                  Destination Type:
                </Typography>
                <Select
                  size="small"
                  value={def?.name ?? ''}
                  onChange={(e) => setSelected(String(e.target.value))}
                  sx={{ minWidth: 200 }}
                >
                  {defs.map((d) => (
                    <MenuItem key={d.name} value={d.name}>
                      {d.schema?.title ?? d.name}
                    </MenuItem>
                  ))}
                </Select>
              </Stack>

              {def && (
                <form onSubmit={handleSubmit}>
                  <Stack spacing={2}>
                    {Object.entries(props).map(([key, meta]) => {
                      const m = meta;
                      const type =
                        m.type === 'string' && m?.['ui:widget'] === 'password'
                          ? 'password'
                          : 'text';
                      return (
                        <TextField
                          key={key}
                          fullWidth
                          type={type}
                          label={m.title ?? key}
                          required={req.has(key)}
                          defaultValue={m.default ?? ''}
                          onChange={(e) =>
                            setValues((prev) => ({ ...prev, [key]: e.target.value }))
                          }
                        />
                      );
                    })}
                    <Stack direction="row" spacing={2} sx={{ mt: 3 }}>
                      <Button
                        variant="contained"
                        type="submit"
                        disabled={createDestinationMutation.isPending}
                      >
                        {createDestinationMutation.isPending ? 'Saving...' : 'Save Destination'}
                      </Button>
                      <Button
                        variant="outlined"
                        onClick={() => {
                          setShowCreateForm(false);
                          setValues({});
                        }}
                      >
                        Cancel
                      </Button>
                    </Stack>
                  </Stack>
                </form>
              )}
            </Stack>
          </Paper>
        </>
      )}

      {/* Edit Destination Dialog */}
      <Dialog
        open={!!editingDestination}
        onClose={() => setEditingDestination(null)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Edit Destination</DialogTitle>
        <form onSubmit={handleUpdateDestination}>
          <DialogContent>
            <Stack spacing={2} sx={{ mt: 1 }}>
              <TextField
                fullWidth
                label="Display Name"
                value={editingDestination?.display_name || ''}
                onChange={(e) =>
                  setEditingDestination((prev) =>
                    prev ? { ...prev, display_name: e.target.value } : null,
                  )
                }
              />
              {editingDestination &&
                defs.find((d) => d.name === editingDestination.name) &&
                Object.entries(
                  defs.find((d) => d.name === editingDestination.name)?.schema?.properties || {},
                ).map(([key, meta]) => {
                  const m = meta;
                  const type =
                    m.type === 'string' && m?.['ui:widget'] === 'password' ? 'password' : 'text';
                  return (
                    <TextField
                      key={key}
                      fullWidth
                      type={type}
                      label={m.title ?? key}
                      value={editValues[key] || ''}
                      onChange={(e) =>
                        setEditValues((prev) => ({ ...prev, [key]: e.target.value }))
                      }
                    />
                  );
                })}
            </Stack>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setEditingDestination(null)}>Cancel</Button>
            <Button
              type="submit"
              variant="contained"
              disabled={updateDestinationMutation.isPending}
            >
              {updateDestinationMutation.isPending ? 'Updating...' : 'Update'}
            </Button>
          </DialogActions>
        </form>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)}>
        <DialogTitle>Delete Destination</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Are you sure you want to delete "{destinationToDelete?.display_name}"? This action
            cannot be undone. Any active syncs using this destination will be stopped.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={confirmDeleteDestination}
            color="error"
            variant="contained"
            disabled={deleteDestinationMutation.isPending}
          >
            {deleteDestinationMutation.isPending ? 'Deleting...' : 'Delete'}
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
}
