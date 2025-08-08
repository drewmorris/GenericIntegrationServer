// @ts-nocheck
import { Table, TableHead, TableRow, TableCell, TableBody, CircularProgress, Typography, Button } from '@mui/material';
import { useProfiles } from '../hooks/useProfiles';

export default function ProfilesList() {
    const { data, isLoading } = useProfiles();

    if (isLoading) return <CircularProgress sx={{ mt: 4 }} />;

    return (
        <>
            <Typography variant="h5" sx={{ mb: 2 }}>Connector Profiles</Typography>
            <Button href="/profiles/new" variant="outlined" size="small" sx={{ mb: 2 }}>New Profile</Button>
            <Table size="small">
                <TableHead>
                    <TableRow>
                        <TableCell>Name</TableCell>
                        <TableCell>Source</TableCell>
                        <TableCell>Every (min)</TableCell>
                    </TableRow>
                </TableHead>
                <TableBody>
                    {data?.map(p => (
                        <TableRow key={p.id} hover>
                            <TableCell component="th" scope="row">
                                <a href={`/profiles/${p.id}/runs`}>{p.name}</a>
                            </TableCell>
                            <TableCell><a href={`/profiles/${p.id}/edit`}>Edit</a></TableCell>
                            <TableCell>{p.source}</TableCell>
                            <TableCell>{p.interval_minutes}</TableCell>
                        </TableRow>
                    ))}
                </TableBody>
            </Table>
        </>
    );
} 