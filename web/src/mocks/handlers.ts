/**
 * MSW request handlers for API mocking
 * Provides realistic API responses for testing and development
 */
import { HttpResponse, http } from 'msw';

// Constants
const MOCK_TIMESTAMP = '2025-01-21T10:00:00Z';

// Mock data
const mockDestinations = [
  {
    id: 'dest-1',
    name: 'cleverbrag',
    displayName: 'CleverBrag',
    config: { api_key: 'cb_test_123' },
    status: 'active',
    createdAt: MOCK_TIMESTAMP,
    updatedAt: MOCK_TIMESTAMP,
  },
  {
    id: 'dest-2',
    name: 'onyx',
    displayName: 'Onyx',
    config: { base_url: 'https://onyx.example.com' },
    status: 'active',
    createdAt: MOCK_TIMESTAMP,
    updatedAt: MOCK_TIMESTAMP,
  },
];

const mockDestinationDefinitions = [
  {
    name: 'cleverbrag',
    displayName: 'CleverBrag',
    description: 'AI-powered knowledge management and retrieval system',
    configSchema: {
      api_key: { type: 'string', required: true },
      base_url: { type: 'string', required: false },
    },
    authType: 'static',
    features: ['AI Search', 'Knowledge Management', 'Real-time Indexing'],
    category: 'Knowledge Management',
  },
  {
    name: 'onyx',
    displayName: 'Onyx',
    description: 'Open-source enterprise search platform',
    configSchema: {
      base_url: { type: 'string', required: true },
      api_key: { type: 'string', required: false },
    },
    authType: 'static',
    features: ['Enterprise Search', 'Document Processing', 'Analytics'],
    category: 'Search',
  },
];

const mockConnectorDefinitions = [
  {
    source: 'gmail',
    name: 'Gmail',
    description: 'Sync emails and attachments from Gmail',
    auth_type: 'oauth',
    category: 'Email & Communication',
  },
  {
    source: 'slack',
    name: 'Slack',
    description: 'Sync messages and files from Slack channels',
    auth_type: 'oauth',
    category: 'Email & Communication',
  },
  {
    source: 'postgres',
    name: 'PostgreSQL',
    description: 'Sync data from PostgreSQL database',
    auth_type: 'static',
    category: 'Databases',
  },
];

export const handlers = [
  // Destinations
  http.get('/api/destinations', () => {
    return HttpResponse.json(mockDestinations);
  }),

  http.post('/api/destinations', async ({ request }) => {
    const body = (await request.json()) as any;
    const newDestination = {
      id: `dest-${Date.now()}`,
      ...body,
      status: 'active',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    return HttpResponse.json(newDestination, { status: 201 });
  }),

  http.get('/api/destinations/definitions', () => {
    return HttpResponse.json(mockDestinationDefinitions);
  }),

  http.post('/api/destinations/:name/test', async ({ params, request }) => {
    const { name } = params;
    const _body = (await request.json()) as any;

    // Simulate test delay
    await new Promise((resolve) => setTimeout(resolve, 1000));

    return HttpResponse.json({
      success: true,
      message: `Connection to ${name || 'destination'} successful`,
      details: {
        connectivity: true,
        authentication: true,
        performance: {
          responseTime: Math.random() * 500 + 200,
          status: 'excellent',
        },
      },
    });
  }),

  // Connectors
  http.get('/api/connectors/definitions', () => {
    return HttpResponse.json(mockConnectorDefinitions);
  }),

  http.post('/api/cc-pairs', async ({ request }) => {
    const body = (await request.json()) as any;
    const newPair = {
      id: `cc-pair-${Date.now()}`,
      ...body,
      status: 'active',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    return HttpResponse.json(newPair, { status: 201 });
  }),

  // Health check
  http.get('/api/health', () => {
    return HttpResponse.json({ status: 'healthy' });
  }),
];
