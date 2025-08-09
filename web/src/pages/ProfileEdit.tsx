import { Container, TextField, Button, CircularProgress, Typography } from '@mui/material';
import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';

import { useSnack } from '../components/Snackbar';
import { useProfiles } from '../hooks/useProfiles';
import { useUpdateProfile } from '../hooks/useUpdateProfile';

export default function ProfileEdit() {
  const { id } = useParams();
  const { data: profiles } = useProfiles();
  const profile = profiles?.find((p) => p.id === id);

  const [name, setName] = useState<string>(profile?.name ?? '');
  const [interval, setInterval] = useState<number>(profile?.interval_minutes ?? 60);

  const { mutateAsync, isPending } = useUpdateProfile();
  const navigate = useNavigate();
  const snack = useSnack();

  if (!profile) return <CircularProgress sx={{ mt: 4 }} />;

  const handleSave = async () => {
    if (!id) return;
    await mutateAsync({ id, payload: { name, interval_minutes: interval } });
    snack.enqueue('Profile updated', { variant: 'success' });
    navigate('/profiles');
  };

  return (
    <Container maxWidth="sm" sx={{ mt: 4 }}>
      <Typography variant="h5" gutterBottom>
        Edit Profile
      </Typography>
      <TextField
        fullWidth
        label="Name"
        margin="normal"
        value={name}
        onChange={(e) => setName(e.target.value)}
      />
      <TextField
        fullWidth
        label="Interval Minutes"
        type="number"
        margin="normal"
        value={interval}
        onChange={(e) => setInterval(Number(e.target.value))}
      />
      <Button variant="contained" onClick={handleSave} disabled={isPending} sx={{ mt: 2 }}>
        Save
      </Button>
    </Container>
  );
}
