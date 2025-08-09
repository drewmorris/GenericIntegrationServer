export type ConnectorProfile = {
  id: string;
  name: string;
  interval_minutes: number;
};

export type SyncRun = {
  id: string;
  status: 'success' | 'failure' | 'pending';
  started_at: string; // ISO timestamp
  finished_at?: string; // ISO timestamp
};
