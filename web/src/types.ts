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

export type IndexAttempt = {
  id: number;
  connector_credential_pair_id: number;
  status: 'NOT_STARTED' | 'IN_PROGRESS' | 'SUCCESS' | 'FAILED' | 'CANCELED';

  // Progress tracking
  new_docs_indexed: number;
  total_docs_indexed: number;
  docs_removed_from_index: number;

  // Batch tracking
  total_batches?: number;
  completed_batches: number;
  total_chunks: number;

  // Progress and heartbeat
  last_progress_time?: string;
  last_batches_completed_count: number;
  heartbeat_counter: number;
  last_heartbeat_value: number;
  last_heartbeat_time?: string;

  // Task coordination
  celery_task_id?: string;
  cancellation_requested: boolean;
  checkpoint_pointer?: string;

  // Timestamps
  time_created: string;
  time_started?: string;
  time_updated?: string;

  // Error tracking
  error_msg?: string;
  full_exception_trace?: string;

  // Related data (if included)
  connector_credential_pair?: {
    id: number;
    name: string;
    connector?: {
      id: number;
      name: string;
      source: string;
    };
  };
};
