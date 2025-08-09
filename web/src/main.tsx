// @ts-nocheck
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';

import { withSnackbar } from './components/Snackbar';
import { AuthProvider } from './context/AuthContext';
import App from './pages/App';

const queryClient = new QueryClient();

ReactDOM.createRoot(document.querySelector('#root') as HTMLElement).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      {withSnackbar(
        <BrowserRouter>
          <AuthProvider>
            <App />
          </AuthProvider>
        </BrowserRouter>,
      )}
    </QueryClientProvider>
  </React.StrictMode>,
);
