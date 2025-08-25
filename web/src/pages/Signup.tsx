import { Box, Button, Container, Link, Stack, Typography } from '@mui/material';
import { useState } from 'react';
import { Link as RouterLink, useNavigate } from 'react-router-dom';
import { ErrorDisplay } from '../components/ErrorDisplay';
import { FormTextField, useFormValidation } from '../components/FormErrorBoundary';
import { useAuth } from '../context/AuthContext';
import { useErrorRecovery } from '../hooks/useGlobalErrorHandler';
import { apiPost } from '../lib/enhanced-api';

export default function Signup() {
  const auth = useAuth();
  const navigate = useNavigate();
  const { withErrorRecovery } = useErrorRecovery();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<Error | null>(null);

  const { values, errors, handleChange, handleBlur, validateAllFields, clearErrors } =
    useFormValidation(
      {
        organization: '',
        email: '',
        password: '',
        confirmPassword: '',
      },
      {
        organization: (value: string) => {
          if (!value.trim()) return 'Organization name is required';
          if (value.trim().length < 2) return 'Organization name must be at least 2 characters';
          return null;
        },
        email: (value: string) => {
          if (!value.trim()) return 'Email is required';
          const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
          if (!emailRegex.test(value.trim())) return 'Please enter a valid email address';
          return null;
        },
        password: (value: string) => {
          if (!value) return 'Password is required';
          if (value.length < 8) return 'Password must be at least 8 characters';
          if (!/(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/.test(value)) {
            return 'Password must contain at least one uppercase letter, one lowercase letter, and one number';
          }
          return null;
        },
        confirmPassword: (value: string) => {
          if (!value) return 'Please confirm your password';
          if (value !== values.password) return 'Passwords do not match';
          return null;
        },
      },
    );

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validateAllFields()) return;

    setIsSubmitting(true);
    setSubmitError(null);

    await withErrorRecovery(
      async () => {
        const data = await apiPost<{ access_token: string; refresh_token: string }>(
          '/auth/signup',
          {
            email: values.email.trim(),
            password: values.password,
            organization: values.organization.trim(),
          },
        );

        auth.login(String(data.access_token), String(data.refresh_token));
        navigate('/');
        return data;
      },
      'Signup',
      {
        showError: false,
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
      <Box textAlign="center" mb={4}>
        <Typography variant="h4" gutterBottom>
          Create Account
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Start syncing your data with the Integration Server
        </Typography>
      </Box>

      {submitError && (
        <ErrorDisplay
          error={submitError}
          variant="alert"
          onRetry={handleRetry}
          sx={{ mb: 3 }}
          title={
            submitError.message?.includes('already exists')
              ? 'Account Already Exists'
              : 'Signup Failed'
          }
        />
      )}

      <form onSubmit={handleSubmit}>
        <FormTextField
          name="organization"
          label="Organization Name"
          value={values.organization}
          error={errors.organization}
          onChange={handleChange}
          onBlur={handleBlur}
          disabled={isSubmitting}
          fullWidth
          margin="normal"
          helperText="This will be your organization's name in the system"
          required
        />

        <FormTextField
          name="email"
          label="Email Address"
          type="email"
          value={values.email}
          error={errors.email}
          onChange={handleChange}
          onBlur={handleBlur}
          disabled={isSubmitting}
          fullWidth
          margin="normal"
          helperText="We'll use this for your account login"
          required
        />

        <FormTextField
          name="password"
          label="Password"
          type="password"
          value={values.password}
          error={errors.password}
          onChange={handleChange}
          onBlur={handleBlur}
          disabled={isSubmitting}
          fullWidth
          margin="normal"
          helperText="At least 8 characters with uppercase, lowercase, and numbers"
          required
        />

        <FormTextField
          name="confirmPassword"
          label="Confirm Password"
          type="password"
          value={values.confirmPassword}
          error={errors.confirmPassword}
          onChange={handleChange}
          onBlur={handleBlur}
          disabled={isSubmitting}
          fullWidth
          margin="normal"
          required
        />

        <Stack direction="row" spacing={2} sx={{ mt: 3 }}>
          <Button
            variant="contained"
            type="submit"
            disabled={isSubmitting || Object.keys(errors).some((key) => errors[key])}
            size="large"
            fullWidth
          >
            {isSubmitting ? 'Creating Account...' : 'Create Account'}
          </Button>
        </Stack>

        <Box textAlign="center" sx={{ mt: 3 }}>
          <Typography variant="body2">
            Already have an account?{' '}
            <Link component={RouterLink} to="/login" underline="hover">
              Sign in here
            </Link>
          </Typography>
        </Box>
      </form>
    </Container>
  );
}
