import { Alert, Box, CircularProgress, Paper, Typography } from '@mui/material';
import { useSnackbar } from 'notistack';
import type React from 'react';
import { useEffect, useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { api } from '../lib/api';

// Helper function to get provider display name
const getProviderDisplayName = (provider: string) =>
  provider === 'gmail' ? 'Gmail' : 'Google Drive';

const OAuthCallback: React.FC = () => {
  const navigate = useNavigate();
  const { provider } = useParams<{ provider: string }>();
  const [searchParams] = useSearchParams();
  const { enqueueSnackbar } = useSnackbar();
  const [status, setStatus] = useState<'processing' | 'success' | 'error'>('processing');
  const [message, setMessage] = useState('Processing OAuth callback...');

  useEffect(() => {
    const handleOAuthCallback = async () => {
      try {
        const code = searchParams.get('code');
        const state = searchParams.get('state');
        const error = searchParams.get('error');

        if (error) {
          throw new Error(`OAuth error: ${error}`);
        }

        if (!code || !state) {
          throw new Error('Missing authorization code or state parameter');
        }

        if (!provider || !['gmail', 'drive'].includes(provider)) {
          throw new Error('Invalid OAuth provider');
        }

        setMessage('Exchanging authorization code for credentials...');

        // Send the authorization code to the backend to complete OAuth
        const endpoint =
          provider === 'gmail' ? '/oauth/google/gmail/callback' : '/oauth/google/drive/callback';

        const response = await api.get(endpoint, {
          params: { code, state },
        });

        if (response.data) {
          setStatus('success');
          const providerName = getProviderDisplayName(provider || '');
          setMessage(`${providerName} OAuth completed successfully!`);

          enqueueSnackbar(`${providerName} credential created: ${response.data.email}`, {
            variant: 'success',
          });

          // Redirect to connectors page with credential info
          setTimeout(() => {
            navigate(
              `/connectors?credential_id=${response.data.credential_id}&connector=${provider === 'gmail' ? 'gmail' : 'google_drive'}`,
            );
          }, 2000);
        }
      } catch (error: any) {
        console.error('OAuth callback error:', error);
        setStatus('error');
        setMessage(error.response?.data?.detail || error.message || 'OAuth callback failed');

        enqueueSnackbar('OAuth authentication failed', { variant: 'error' });

        // Redirect back to connectors page after error
        setTimeout(() => {
          navigate('/connectors');
        }, 3000);
      }
    };

    void handleOAuthCallback();
  }, [searchParams, provider, navigate, enqueueSnackbar]);

  const getIcon = () => {
    switch (status) {
      case 'processing': {
        return <CircularProgress size={48} />;
      }
      case 'success': {
        return <Typography variant="h2">✅</Typography>;
      }
      case 'error': {
        return <Typography variant="h2">❌</Typography>;
      }
    }
  };

  const getColor = () => {
    switch (status) {
      case 'processing': {
        return 'info';
      }
      case 'success': {
        return 'success';
      }
      case 'error': {
        return 'error';
      }
    }
  };

  return (
    <Box
      display="flex"
      justifyContent="center"
      alignItems="center"
      minHeight="100vh"
      bgcolor="background.default"
    >
      <Paper
        elevation={3}
        sx={{
          p: 4,
          maxWidth: 500,
          width: '100%',
          textAlign: 'center',
        }}
      >
        <Box mb={3}>{getIcon()}</Box>

        <Typography variant="h5" gutterBottom>
          {provider === 'gmail' ? 'Gmail' : 'Google Drive'} OAuth
        </Typography>

        <Alert severity={getColor()} sx={{ mt: 2 }}>
          {message}
        </Alert>

        {status === 'success' && (
          <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
            Redirecting to connectors page...
          </Typography>
        )}

        {status === 'error' && (
          <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
            Redirecting back to connectors page...
          </Typography>
        )}
      </Paper>
    </Box>
  );
};

export default OAuthCallback;
