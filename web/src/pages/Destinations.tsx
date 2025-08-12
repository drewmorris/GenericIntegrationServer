import { Container, Typography, Paper, MenuItem, Select, TextField, Button, Stack, Alert } from '@mui/material';
import { useMemo, useState } from 'react';
import { useDestinationDefinitions, type DestinationDefinition } from '../hooks/useDestinations';

export default function DestinationsPage() {
    const { data, isLoading, error, refetch } = useDestinationDefinitions();
    const defs: DestinationDefinition[] = Array.isArray(data) ? data : [];
    const [selected, setSelected] = useState<string>('');
    const def: DestinationDefinition | undefined = useMemo(
        () => (defs.length ? defs.find((d) => d.name === selected) || defs[0] : undefined),
        [defs, selected],
    );
    const [values, setValues] = useState<Record<string, string>>({});

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
                <Alert severity="error" sx={{ mb: 2 }}>Failed to load destinations: {String(error.message)}</Alert>
                <Button variant="outlined" onClick={() => void refetch()}>Retry</Button>
            </Container>
        );
    }

    if (!defs.length) {
        return (
            <Container maxWidth="md" sx={{ mt: 4 }}>
                <Alert severity="info" sx={{ mb: 2 }}>No destinations found.</Alert>
                <Stack direction="row" spacing={2}>
                    <Button variant="outlined" onClick={() => void refetch()}>Refresh</Button>
                    <Button variant="contained" onClick={() => void refetch()}>Add Destination</Button>
                </Stack>
            </Container>
        );
    }

    const props = def?.schema?.properties ?? {};
    const req = new Set<string>(def?.schema?.required ?? []);

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (!def) return;
        const orgId = localStorage.getItem('org_id');
        if (!orgId) {
            alert('No organization selected');
            return;
        }
        const userId = localStorage.getItem('user_id');
        if (!userId) {
            alert('No user selected');
            return;
        }
        const payload = {
            organization_id: orgId,
            user_id: userId,
            name: def.name,
            display_name: def.schema?.title || def.name,
            config: values,
        } as any;
        fetch((import.meta as any)?.env?.VITE_API_BASE ? `${(import.meta as any).env.VITE_API_BASE}/targets` : 'http://localhost:8000/targets', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        })
            .then(async (r) => {
                if (!r.ok) throw new Error(await r.text());
                alert('Destination saved');
            })
            .catch((err) => alert(`Failed to save: ${String(err)}`));
    };

    return (
        <Container maxWidth="md" sx={{ mt: 4 }}>
            <Typography variant="h4" gutterBottom>
                Destinations
            </Typography>
            <Paper sx={{ p: 2 }}>
                <Stack spacing={2}>
                    <Stack direction="row" spacing={2} alignItems="center">
                        <Select
                            size="small"
                            value={def?.name ?? ''}
                            onChange={(e) => setSelected(String(e.target.value))}
                        >
                            {defs.map((d) => (
                                <MenuItem key={d.name} value={d.name}>
                                    {d.schema?.title ?? d.name}
                                </MenuItem>
                            ))}
                        </Select>
                        <Button variant="contained" onClick={() => { /* future: add new target instance */ }}>
                            Add Destination
                        </Button>
                    </Stack>

                    {def && (
                        <form onSubmit={handleSubmit}>
                            <Stack spacing={2}>
                                {Object.entries(props).map(([key, meta]) => {
                                    const m = meta as any;
                                    const type = m.type === 'string' && m?.['ui:widget'] === 'password' ? 'password' : 'text';
                                    return (
                                        <TextField
                                            key={key}
                                            fullWidth
                                            type={type}
                                            label={m.title ?? key}
                                            required={req.has(key)}
                                            defaultValue={m.default ?? ''}
                                            onChange={(e) => setValues((prev) => ({ ...prev, [key]: e.target.value }))}
                                        />
                                    );
                                })}
                                <Button variant="contained" type="submit">
                                    Save
                                </Button>
                            </Stack>
                        </form>
                    )}
                </Stack>
            </Paper>
        </Container>
    );
} 