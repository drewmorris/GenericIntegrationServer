// @ts-nocheck
import { render, screen } from '@testing-library/react';

import { BrowserRouter } from 'react-router-dom';

import { AuthProvider } from '../context/AuthContext';
import { withSnackbar } from '../components/Snackbar';

import Login from '../pages/Login';

it('renders login heading', () => {
  render(
    withSnackbar(
      <AuthProvider>
        <BrowserRouter>
          <Login />
        </BrowserRouter>
      </AuthProvider>,
    ),
  );
  expect(screen.getByRole('heading', { name: /login/i })).toBeInTheDocument();
});
