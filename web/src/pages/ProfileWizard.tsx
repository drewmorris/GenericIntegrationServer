import {
  Alert,
  Button,
  Container,
  MenuItem,
  Paper,
  Stack,
  Step,
  StepLabel,
  Stepper,
  TextField,
  Typography,
} from '@mui/material';
import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { v4 as uuidv4 } from 'uuid';

import { useSnack } from '../components/Snackbar';
import { useConnectorDefinitions } from '../hooks/useConnectorDefinitions';
import { useCreateProfile } from '../hooks/useCreateProfile';
import { useCredentials } from '../hooks/useCredentials';
import { useDestinationDefinitions } from '../hooks/useDestinationDefinitions';
import { api } from '../lib/api';

const steps = ['Basics', 'Connector', 'Destination', 'Review'];

export default function ProfileWizard() {
  const [activeStep, setActiveStep] = useState(0);
  const [name, setName] = useState('');

  const {
    data: connectorDefs = [],
    isLoading: loadingConn,
    error: errorConn,
  } = useConnectorDefinitions();
  const {
    data: destinationDefs = [],
    isLoading: loadingDest,
    error: errorDest,
  } = useDestinationDefinitions();

  const [connector, setConnector] = useState<string>('mock_source');
  const connDef = useMemo(
    () => connectorDefs.find((c) => c.name === connector) || connectorDefs[0],
    [connectorDefs, connector],
  );
  const [connectorValues, setConnectorValues] = useState<Record<string, string>>({});
  const orgId = localStorage.getItem('org_id') ?? '';
  const userId = localStorage.getItem('user_id') ?? '';
  const { data: creds = [] } = useCredentials({
    organization_id: orgId,
    user_id: userId,
    connector_name: connector,
  });
  const [credentialId, setCredentialId] = useState<string>('');
  const testCredential = async () => {
    if (!credentialId) {
      snack.enqueue('Select a credential first', { variant: 'info' });
      return;
    }
    try {
      const { data } = await api.post<{ ok: boolean; detail?: string }>(
        `/credentials/${credentialId}/test`,
      );
      snack.enqueue(data.ok ? 'Credential OK' : `Credential failed: ${data.detail ?? 'unknown'}`, {
        variant: data.ok ? 'success' : 'error',
      });
    } catch {
      snack.enqueue('Credential test failed', { variant: 'error' });
    }
  };

  const [destination, setDestination] = useState<string>('cleverbrag');
  const destDef = useMemo(
    () => destinationDefs.find((d) => d.name === destination) || destinationDefs[0],
    [destinationDefs, destination],
  );
  const [destinationValues, setDestinationValues] = useState<Record<string, string>>({});

  const { mutateAsync, isPending } = useCreateProfile();
  const snack = useSnack();
  const navigate = useNavigate();

  const handleNext = async () => {
    if (activeStep === steps.length - 1) {
      const orgId = localStorage.getItem('org_id') ?? uuidv4();
      const userId = localStorage.getItem('user_id') ?? uuidv4();
      await mutateAsync({
        organization_id: orgId,
        user_id: userId,
        name,
        source: connector,
        interval_minutes: 60,
        connector_config: {
          destination,
          [destination]: destinationValues,
          [connector]: connectorValues,
        },
        credential_id: credentialId || undefined,
      });
      navigate('/profiles');
      snack.enqueue('Profile created', { variant: 'success' });
    } else {
      setActiveStep((s) => s + 1);
    }
  };
  const handleBack = () => setActiveStep((s) => s - 1);

  if (loadingConn || loadingDest)
    return (
      <Container maxWidth="sm" sx={{ mt: 4 }}>
        <Typography>Loading…</Typography>
      </Container>
    );
  if (errorConn || errorDest)
    return (
      <Container maxWidth="sm" sx={{ mt: 4 }}>
        <Alert severity="error">Failed to load definitions</Alert>
      </Container>
    );

  const renderSchemaForm = (
    schema?: any,
    _values?: Record<string, string>,
    setValues?: (fn: any) => void,
  ) => {
    const props = schema?.properties ?? {};
    const req = new Set<string>(schema?.required ?? []);
    return (
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
              onChange={(e) => setValues?.((prev: any) => ({ ...prev, [key]: e.target.value }))}
            />
          );
        })}
      </Stack>
    );
  };

  return (
    <Container maxWidth="sm" sx={{ mt: 4 }}>
      <Stepper activeStep={activeStep} alternativeLabel>
        {steps.map((label) => (
          <Step key={label}>
            <StepLabel>{label}</StepLabel>
          </Step>
        ))}
      </Stepper>

      {activeStep === 0 && (
        <TextField
          fullWidth
          label="Profile Name"
          margin="normal"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
      )}

      {activeStep === 1 && (
        <Paper sx={{ p: 2, mt: 2 }}>
          <TextField
            select
            fullWidth
            label="Connector"
            margin="normal"
            value={connector}
            onChange={(e) => setConnector(e.target.value)}
          >
            {connectorDefs.map((c) => (
              <MenuItem key={c.name} value={c.name}>
                {c.schema?.title ?? c.name}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            select
            fullWidth
            label="Credential"
            margin="normal"
            value={credentialId}
            onChange={(e) => setCredentialId(e.target.value)}
            helperText={
              creds.length > 0
                ? 'Select an existing credential for this connector'
                : 'No credentials found; create one in Connectors page'
            }
          >
            {creds.map((cr) => (
              <MenuItem key={cr.id} value={cr.id}>
                {cr.provider_key}
              </MenuItem>
            ))}
          </TextField>
          <Stack direction="row" spacing={1}>
            <Button
              variant="outlined"
              size="small"
              onClick={testCredential}
              disabled={!credentialId}
            >
              Test Connection
            </Button>
          </Stack>
          {renderSchemaForm(connDef?.schema, connectorValues, setConnectorValues)}
        </Paper>
      )}

      {activeStep === 2 && (
        <Paper sx={{ p: 2, mt: 2 }}>
          <TextField
            select
            fullWidth
            label="Destination"
            margin="normal"
            value={destination}
            onChange={(e) => setDestination(e.target.value)}
          >
            {destinationDefs.map((d) => (
              <MenuItem key={d.name} value={d.name}>
                {d.schema?.title ?? d.name}
              </MenuItem>
            ))}
          </TextField>
          {renderSchemaForm(destDef?.schema, destinationValues, setDestinationValues)}
        </Paper>
      )}

      {activeStep === 3 && (
        <Typography sx={{ mt: 2 }}>
          Ready to create profile "{name}" → {connector} → {destination}
        </Typography>
      )}

      <Button disabled={activeStep === 0} onClick={handleBack} sx={{ mt: 2, mr: 1 }}>
        Back
      </Button>
      <Button variant="contained" onClick={handleNext} sx={{ mt: 2 }} disabled={isPending}>
        {activeStep === steps.length - 1 ? 'Create' : 'Next'}
      </Button>
    </Container>
  );
}
