// @ts-nocheck
import { SnackbarProvider, useSnackbar } from 'notistack';
import React, { createContext, useContext } from 'react';

const SnackContext = createContext({ enqueue: (msg: string, variant?: any) => { } });

export function GlobalSnackbarProvider({ children }: { children: React.ReactNode }) {
    const { enqueueSnackbar } = useSnackbar();
    return <SnackContext.Provider value={{ enqueue: enqueueSnackbar }}>{children}</SnackContext.Provider>;
}

export const useSnack = () => useContext(SnackContext);

export function withSnackbar(ui: React.ReactNode) {
    return (
        <SnackbarProvider maxSnack={3} autoHideDuration={3000} anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}>
            <GlobalSnackbarProvider>{ui}</GlobalSnackbarProvider>
        </SnackbarProvider>
    );
} 