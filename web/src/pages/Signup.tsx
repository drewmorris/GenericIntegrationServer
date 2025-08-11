import { TextField, Button, Container, Typography } from '@mui/material';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { useAuth } from '../context/AuthContext';
import { api } from '../lib/api';

export default function Signup() {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [org, setOrg] = useState('');
    const auth = useAuth();
    const navigate = useNavigate();

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            const { data } = await api.post<{ access_token: string; refresh_token: string }>(
                '/auth/signup',
                {
                    email,
                    password,
                    org_name: org,
                },
            );
            auth.login(String(data.access_token), String(data.refresh_token));
            navigate('/');
        } catch {
            alert('Signup failed');
        }
    };

    return (
        <Container maxWidth="sm" sx={{ mt: 8 }}>
            {/* eslint-disable-next-line react/no-unknown-property */}
            <Typography variant="h4" gutterBottom>
                Sign Up
            </Typography>
            <form onSubmit={handleSubmit}>
                <TextField
                    fullWidth
                    label="Organization Name"
                    margin="normal"
                    value={org}
                    onChange={(e) => setOrg(e.target.value)}
                />
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
                <Button variant="contained" type="submit" sx={{ mt: 2 }}>
                    Create Account
                </Button>
            </form>
        </Container>
    );
} 