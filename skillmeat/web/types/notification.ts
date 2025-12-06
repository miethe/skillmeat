/**
 * Notification Types for SkillMeat Web Interface
 *
 * These types represent notifications for imports, syncs, errors, and system events.
 */

/**
 * Type of notification event
 */
export type NotificationType = 'import' | 'sync' | 'error' | 'info' | 'success';

/**
 * Read/unread status of a notification
 */
export type NotificationStatus = 'read' | 'unread';

/**
 * Type of artifact being imported or synced
 */
export type ArtifactType = 'skill' | 'command' | 'agent' | 'mcp' | 'hook';

/**
 * Result of a single artifact import operation
 */
export interface ArtifactImportResult {
  /** Name of the artifact */
  name: string;
  /** Type of artifact */
  type: ArtifactType;
  /** Whether the import succeeded */
  success: boolean;
  /** Error message if the import failed */
  error?: string;
}

/**
 * Detailed results of a batch import operation
 */
export interface ImportResultDetails {
  /** Total number of artifacts in the batch */
  total: number;
  /** Number of successful imports */
  succeeded: number;
  /** Number of failed imports */
  failed: number;
  /** Individual artifact results */
  artifacts: ArtifactImportResult[];
}

/**
 * Error notification details
 */
export interface ErrorDetails {
  /** Error code if available */
  code?: string;
  /** Error message */
  message: string;
  /** Optional stack trace */
  stack?: string;
  /** Whether the error is retryable */
  retryable?: boolean;
}

/**
 * Generic notification details for info/success/warning notifications
 */
export interface GenericDetails {
  /** Metadata key-value pairs */
  metadata?: Record<string, string | number | boolean>;
}

/**
 * Import status for individual artifact in bulk import
 */
export type ImportStatus = 'success' | 'skipped' | 'failed';

/**
 * Single artifact result in bulk import
 */
export interface BulkImportArtifactResult {
  /** Artifact ID (format: type:name) */
  artifact_id: string;
  /** Import status */
  status: ImportStatus;
  /** Status message */
  message: string;
  /** Error message if failed */
  error?: string;
  /** Skip reason if skipped */
  skip_reason?: string;
}

/**
 * Detailed results of a bulk import operation
 * Matches backend BulkImportResult schema
 */
export interface BulkImportResultDetails {
  /** Total number of artifacts requested */
  total_requested: number;
  /** Total successfully imported */
  total_imported: number;
  /** Total skipped */
  total_skipped: number;
  /** Total failed */
  total_failed: number;
  /** Imported to collection (new artifacts) */
  imported_to_collection: number;
  /** Added to project (deployed artifacts) */
  added_to_project: number;
  /** Individual artifact results */
  results: BulkImportArtifactResult[];
  /** Operation duration in milliseconds */
  duration_ms?: number;
  /** Summary message */
  summary?: string;
}

/**
 * Union type for all notification detail types
 */
export type NotificationDetails = ImportResultDetails | ErrorDetails | GenericDetails | BulkImportResultDetails;

/**
 * Complete notification data structure
 */
export interface NotificationData {
  /** Unique identifier */
  id: string;
  /** Type of notification */
  type: NotificationType;
  /** Notification title */
  title: string;
  /** Notification message */
  message: string;
  /** When the notification was created */
  timestamp: Date;
  /** Read/unread status */
  status: NotificationStatus;
  /** Optional detailed results for import/sync/error operations */
  details?: NotificationDetails | null;
}

/**
 * Input data for creating a new notification (without id/timestamp)
 *
 * Use this type when adding notifications to the store.
 * The store will automatically generate id and timestamp.
 */
export interface NotificationCreateInput {
  /** Type of notification */
  type: NotificationType;
  /** Notification title */
  title: string;
  /** Notification message */
  message: string;
  /** Read/unread status (defaults to 'unread') */
  status?: NotificationStatus;
  /** Optional detailed results for import/sync/error operations */
  details?: NotificationDetails | null;
}

/**
 * Notification store state shape
 *
 * Represents the complete state managed by the notification store.
 */
export interface NotificationStoreState {
  /** All notifications, newest first */
  notifications: NotificationData[];
  /** Count of unread notifications */
  unreadCount: number;
}

/**
 * Notification store actions
 *
 * Methods available for managing notifications in the store.
 */
export interface NotificationStoreActions {
  /**
   * Add a new notification to the store
   * @param notification - Notification data (id and timestamp will be generated)
   */
  addNotification: (notification: NotificationCreateInput) => void;

  /**
   * Mark a specific notification as read
   * @param id - Notification ID
   */
  markAsRead: (id: string) => void;

  /**
   * Mark all notifications as read
   */
  markAllAsRead: () => void;

  /**
   * Remove a specific notification
   * @param id - Notification ID
   */
  dismissNotification: (id: string) => void;

  /**
   * Clear all notifications
   */
  clearAll: () => void;
}

/**
 * Combined notification store type
 *
 * Use this type when defining the Zustand store.
 */
export type NotificationStore = NotificationStoreState & NotificationStoreActions;
