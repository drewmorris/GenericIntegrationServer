// @ts-nocheck
import { useState } from 'react';
import { TextField, Button, Container, Typography } from '@mui/material';
import { useAuth } from '../context/AuthContext';
import { api } from '../lib/api';
import { useNavigate } from 'react-router-dom';

export default function Login() {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const auth = useAuth();
    const navigate = useNavigate();
    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            const { data } = await api.post('/auth/login', { email, password });
            auth.login(data.access_token, data.refresh_token);
            navigate('/');
        } catch (err) {
            alert('Login failed');
        }
    };
    return (
        <Container maxWidth="sm" sx={{ mt: 8 }}>
            <Typography variant="h4" gutterBottom>Login</Typography>
            <form onSubmit={handleSubmit}>
                <TextField fullWidth label="Email" margin="normal" value={email} onChange={e => setEmail(e.target.value)} />
                <TextField fullWidth type="password" label="Password" margin="normal" value={password} onChange={e => setPassword(e.target.value)} />
                <Button variant="contained" type="submit" sx={{ mt: 2 }}>Login</Button>
            </form>
        </Container>
    );
} 