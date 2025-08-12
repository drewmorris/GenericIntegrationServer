// @ts-nocheck
import {
  Table,
  TableHead,
  TableRow,
  TableCell,
  TableBody,
  CircularProgress,
  Typography,
  Button,
} from '@mui/material';
import { Link as RouterLink } from 'react-router-dom';

import { useProfiles } from '../hooks/useProfiles';

export default function ProfilesList() {
  const { data, isLoading } = useProfiles();

  if (isLoading) return <CircularProgress sx={{ mt: 4 }} />;

  return (
    <>
      <Typography variant="h5" sx={{ mb: 2 }}>
        Connector Profiles
      </Typography>
      <Button component={RouterLink} to="/profiles/new" variant="outlined" size="small" sx={{ mb: 2 }}>
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
