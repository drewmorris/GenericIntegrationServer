// @ts-nocheck
import { useParams } from 'react-router-dom';
import { useSyncRuns } from '../hooks/useSyncRuns';
import { Table, TableHead, TableRow, TableCell, TableBody, CircularProgress, Typography, Chip } from '@mui/material';

export default function SyncRunsPage() {
    const { id } = useParams();
    const { data, isLoading } = useSyncRuns(id!);
    if (isLoading) return <CircularProgress sx={{ mt: 4 }} />;
    return (
        <>
            <Typography variant="h5" sx={{ mb: 2 }}>Sync Runs</Typography>
            <Table size="small">
                <TableHead>
                    <TableRow>
                        <TableCell>Started</TableCell>
                        <TableCell>Finished</TableCell>
                        <TableCell>Status</TableCell>
                    </TableRow>
                </TableHead>
                <TableBody>
                    {data?.map(r => (
                        <TableRow key={r.id} hover>
                            <TableCell>{new Date(r.started_at).toLocaleString()}</TableCell>
                            <TableCell>{r.finished_at ? new Date(r.finished_at).toLocaleString() : '-'}</TableCell>
                            <TableCell><Chip label={r.status} color={r.status === 'success' ? 'success' : r.status === 'failure' ? 'error' : 'warning'} size="small" /></TableCell>
                        </TableRow>
                    ))}
                </TableBody>
            </Table>
        </>
    );
} 