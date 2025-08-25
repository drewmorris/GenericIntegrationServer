// @ts-nocheck
import {
  Box,
  Button,
  CircularProgress,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material';
import { Link as RouterLink } from 'react-router-dom';

import { ErrorDisplay } from '../components/ErrorDisplay';
import { useProfiles } from '../hooks/useProfiles';

export default function ProfilesList() {
  const { data, isLoading, error, refetch } = useProfiles();

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="200px">
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ mt: 4 }}>
        <ErrorDisplay
          error={error}
          title="Failed to load profiles"
          variant="card"
          onRetry={() => refetch()}
        />
      </Box>
    );
  }

  return (
    <>
      <Typography variant="h5" sx={{ mb: 2 }}>
        Connector Profiles
      </Typography>
      <Button
        component={RouterLink}
        to="/profiles/new"
        variant="outlined"
        size="small"
        sx={{ mb: 2 }}
      >
        New Profile
      </Button>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Name</TableCell>
            <TableCell>Source</TableCell>
            <TableCell>Every (min)</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {data?.map((p) => (
            <TableRow key={p.id} hover>
              <TableCell component="th" scope="row">
                <RouterLink to={`/profiles/${p.id}/runs`}>{p.name}</RouterLink>
              </TableCell>
              <TableCell>
                <RouterLink to={`/profiles/${p.id}/edit`}>Edit</RouterLink>
              </TableCell>
              <TableCell>{p.source}</TableCell>
              <TableCell>{p.interval_minutes}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </>
  );
}
