import { Button, Container, Link, Stack, Typography } from '@mui/material';
import { useState } from 'react';
import { Link as RouterLink, useNavigate } from 'react-router-dom';

import { ErrorDisplay } from '../components/ErrorDisplay';
import { useFormValidation, ValidatedTextField } from '../components/FormErrorBoundary';
import { useAuth } from '../context/AuthContext';
import { useErrorRecovery } from '../hooks/useGlobalErrorHandler';
import { apiPost } from '../lib/enhanced-api';

export default function Login() {
  const auth = useAuth();
  const navigate = useNavigate();
  const { withErrorRecovery } = useErrorRecovery();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<Error | null>(null);

  const { values, errors, handleChange, handleBlur, validateAllFields, clearErrors } =
    useFormValidation(
      { email: '', password: '' },
      {
        email: (value: string) => {
          if (!value) return 'Email is required';
          if (!/\S+@\S+\.\S+/.test(value)) return 'Invalid email format';
          return null;
        },
        password: (value: string) => {
          if (!value) return 'Password is required';
          if (value.length < 6) return 'Password must be at least 6 characters';
          return null;
        },
      },
    );

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateAllFields()) {
      return;
    }

    setIsSubmitting(true);
    setSubmitError(null);

    await withErrorRecovery(
      async () => {
        const data = await apiPost<{ access_token: string; refresh_token: string }>('/auth/login', {
          email: values.email,
          password: values.password,
        });

        auth.login(String(data.access_token), String(data.refresh_token));
        navigate('/');
        return data;
      },
      'Login',
      {
        showError: false, // We'll handle error display manually
        onError: (error) => {
          setSubmitError(error);
        },
      },
    );

    setIsSubmitting(false);
  };

  const handleRetry = () => {
    setSubmitError(null);
    clearErrors();
  };
  return (
    <Container maxWidth="sm" sx={{ mt: 8 }}>
      <Typography variant="h4" gutterBottom>
        Login
      </Typography>

      {submitError && (
        <ErrorDisplay error={submitError} variant="alert" onRetry={handleRetry} sx={{ mb: 3 }} />
      )}

      <form onSubmit={handleSubmit}>
        <ValidatedTextField
          fullWidth
          label="Email"
          type="email"
          margin="normal"
          value={values.email}
          onChange={(e) => handleChange('email', e.target.value)}
          onBlur={() => handleBlur('email')}
          validation={{
            required: true,
            pattern: /\S+@\S+\.\S+/,
          }}
          showValidation
          disabled={isSubmitting}
        />

        <ValidatedTextField
          fullWidth
          type="password"
          label="Password"
          margin="normal"
          value={values.password}
          onChange={(e) => handleChange('password', e.target.value)}
          onBlur={() => handleBlur('password')}
          validation={{
            required: true,
            minLength: 6,
          }}
          showValidation
          disabled={isSubmitting}
        />

        <Stack direction="row" spacing={2} sx={{ mt: 3 }}>
          <Button
            variant="contained"
            type="submit"
            disabled={isSubmitting || Object.keys(errors).some((key) => errors[key])}
            size="large"
          >
            {isSubmitting ? 'Signing in...' : 'Sign In'}
          </Button>
          <Link component={RouterLink} to="/signup" underline="hover">
            Create an account
          </Link>
        </Stack>
      </form>
    </Container>
  );
}
