/**
 * Mock Service Worker (MSW) server setup
 * Provides API mocking for testing and development
 */
import { setupServer } from 'msw/node';
import { handlers } from './handlers';

// Setup server with request handlers
export const server = setupServer(...handlers);
