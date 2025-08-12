import { useEffect, useMemo, useState } from 'react';
import { Container, Typography, Paper, Stack, Select, MenuItem, Button, Alert, TextField, Divider } from '@mui/material';
import { useConnectorDefinitions } from '../hooks/useConnectors';
import { useCredentials } from '../hooks/useCredentials';
import { api } from '../lib/api';

function randState(): string {
    try {
        // Prefer crypto if available
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const c: any = (window as any).crypto || (window as any).msCrypto;
        if (c?.getRandomValues) {
            const arr = new Uint8Array(16);
            c.getRandomValues(arr);
            return Array.from(arr).map((b) => b.toString(16).padStart(2, '0')).join('');
        }
    } catch { }
    return Math.random().toString(36).slice(2) + Math.random().toString(36).slice(2);
}

export default function ConnectorsPage() {
    const { data: defs = [], isLoading, error } = useConnectorDefinitions();
    const [selected, setSelected] = useState<string>('');
    const def = useMemo(() => (defs.length ? defs.find((d) => d.name === selected) || defs[0] : undefined), [defs, selected]);

    const orgId = localStorage.getItem('org_id') ?? '';
    const userId = localStorage.getItem('user_id') ?? '';
    const { data: creds = [], refetch } = useCredentials({ organization_id: orgId, user_id: userId, connector_name: def?.name });
    const [message, setMessage] = useState<string | null>(null);

    // show success if redirected back with credential_id
    useEffect(() => {
        const url = new URL(window.location.href);
        const created = url.searchParams.get('credential_id');
        if (created) {
            setMessage(`Credential created: ${created}`);
            void refetch();
            url.searchParams.delete('credential_id');
            window.history.replaceState({}, document.title, url.toString());
        }
    }, [refetch]);

    const startOAuth = async () => {
        if (!def) return;
        try {
            const state = randState();
            const next = `${window.location.origin}/connectors`;
            const { data } = await api.get<{ authorization_url: string }>(`/oauth/${def.name}/start`, {
                params: { state, organization_id: orgId, user_id: userId, next },
            });
            window.location.href = data.authorization_url;
        } catch (e) {
            setMessage('OAuth not supported or failed to start.');
        }
    };

    const [providerKey, setProviderKey] = useState('default');
    const [jsonText, setJsonText] = useState('{}');
    const saveStatic = async () => {
        if (!def) return;
        try {
            const payload = JSON.parse(jsonText);
            await api.post('/credentials', {
                organization_id: orgId,
                user_id: userId,
                connector_name: def.name,
                provider_key: providerKey || 'default',
                credential_json: payload,
            });
            setMessage('Credential saved');
            setJsonText('{}');
            void refetch();
        } catch (e) {
            setMessage('Failed to save credential (ensure JSON is valid).');
        }
    };

    if (isLoading) return <Container sx={{ mt: 4 }}><Typography>Loading…</Typography></Container>;
    if (error) return <Container sx={{ mt: 4 }}><Alert severity="error">Failed to load connectors</Alert></Container>;

    return (
        <Container maxWidth="md" sx={{ mt: 4 }}>
            <Typography variant="h4" gutterBottom>Connectors</Typography>
            {message && <Alert sx={{ mb: 2 }} onClose={() => setMessage(null)}>{message}</Alert>}
            <Paper sx={{ p: 2 }}>
                <Stack spacing={2}>
                    <Select size="small" value={def?.name ?? ''} onChange={(e) => setSelected(String(e.target.value))}>
                        {defs.map((d) => (
                            <MenuItem key={d.name} value={d.name}>{d.schema?.title ?? d.name}</MenuItem>
                        ))}
                    </Select>

                    <Typography variant="h6">Existing Credentials</Typography>
                    {creds.length === 0 ? (
                        <Alert severity="info">No credentials for this connector.</Alert>
                    ) : (
                        <Paper variant="outlined" sx={{ p: 1 }}>
                            <Stack spacing={1}>
                                {creds.map((c) => (
                                    <div key={c.id}>{c.provider_key} — {c.id}</div>
                                ))}
                            </Stack>
                        </Paper>
                    )}
                    <Button variant="outlined" onClick={() => void refetch()}>Refresh</Button>

                    <Divider sx={{ my: 1 }} />
                    <Typography variant="h6">Connect via OAuth</Typography>
                    <Button variant="contained" onClick={startOAuth}>Start OAuth</Button>

                    <Divider sx={{ my: 1 }} />
                    <Typography variant="h6">Add Static Credential</Typography>
                    <TextField label="Provider Key" fullWidth margin="dense" value={providerKey} onChange={(e) => setProviderKey(e.target.value)} />
                    <TextField label="Credential JSON" fullWidth margin="dense" value={jsonText} onChange={(e) => setJsonText(e.target.value)} multiline minRows={4} />
                    <Button variant="contained" onClick={saveStatic}>Save Credential</Button>
                </Stack>
            </Paper>
        </Container>
    );
} 