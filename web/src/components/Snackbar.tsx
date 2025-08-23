import { SnackbarProvider, useSnackbar, type VariantType } from 'notistack';
import type React from 'react';
import { createContext, useContext } from 'react';

type SnackContextValue = {
  enqueue: (msg: string, options?: { variant?: VariantType }) => void;
};

const SnackContext = createContext<SnackContextValue>({ enqueue: () => {} });

export function GlobalSnackbarProvider({ children }: { children: React.ReactNode }) {
  const { enqueueSnackbar } = useSnackbar();
  return (
    <SnackContext.Provider value={{ enqueue: enqueueSnackbar }}>{children}</SnackContext.Provider>
  );
}

export const useSnack = () => useContext(SnackContext);

export function withSnackbar(ui: React.ReactNode) {
  return (
    <SnackbarProvider
      maxSnack={3}
      autoHideDuration={3000}
      anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
    >
      <GlobalSnackbarProvider>{ui}</GlobalSnackbarProvider>
    </SnackbarProvider>
  );
}
