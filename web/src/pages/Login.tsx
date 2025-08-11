import { TextField, Button, Container, Typography, Link, Stack } from '@mui/material';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Link as RouterLink } from 'react-router-dom';

import { useAuth } from '../context/AuthContext';
import { api } from '../lib/api';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const auth = useAuth();
  const navigate = useNavigate();
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const { data } = await api.post<{ access_token: string; refresh_token: string }>(
        '/auth/login',
        {
          email,
          password,
        },
      );
      auth.login(String(data.access_token), String(data.refresh_token));
      navigate('/');
    } catch {
      alert('Login failed');
    }
  };
  return (
    <Container maxWidth="sm" sx={{ mt: 8 }}>
      {/* eslint-disable-next-line react/no-unknown-property */}
      <Typography variant="h4" gutterBottom>
        Login
      </Typography>
      <form onSubmit={handleSubmit}>
        <TextField
          fullWidth
          label="Email"
          margin="normal"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <TextField
          fullWidth
          type="password"
          label="Password"
          margin="normal"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <Stack direction="row" spacing={2} sx={{ mt: 2 }}>
          <Button variant="contained" type="submit">
            Login
          </Button>
          <Link component={RouterLink} to="/signup" underline="hover">
            Create an account
          </Link>
        </Stack>
      </form>
    </Container>
  );
}
