/**
 * Server-Sent Events (SSE) hook for real-time analytics updates
 *
 * This hook manages SSE connection for live analytics data.
 * Falls back to polling if SSE is not available.
 */

import { useEffect, useState, useCallback, useRef } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import type { AnalyticsEvent } from '@/types/analytics';

import { apiConfig } from '@/lib/api';

// Environment configuration
const API_BASE_URL = apiConfig.baseUrl;
const API_VERSION = apiConfig.version;
const API_KEY = apiConfig.apiKey || 'dev-key-12345';

export interface UseAnalyticsStreamOptions {
  enabled?: boolean;
  onEvent?: (event: AnalyticsEvent) => void;
  onError?: (error: Error) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
}

export interface AnalyticsStreamStatus {
  isConnected: boolean;
  isConnecting: boolean;
  error: Error | null;
  lastUpdate: Date | null;
  eventCount: number;
}

/**
 * Hook to manage analytics SSE stream
 *
 * Currently uses polling as fallback until SSE endpoint is implemented.
 * Will automatically upgrade to SSE when available.
 */
export function useAnalyticsStream(options: UseAnalyticsStreamOptions = {}) {
  const { enabled = true, onEvent, onError, onConnect, onDisconnect } = options;

  const [status, setStatus] = useState<AnalyticsStreamStatus>({
    isConnected: false,
    isConnecting: false,
    error: null,
    lastUpdate: null,
    eventCount: 0,
  });

  const queryClient = useQueryClient();
  const eventSourceRef = useRef<EventSource | null>(null);
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const isMountedRef = useRef(true);

  /**
   * Handle incoming analytics event
   */
  const handleEvent = useCallback(
    (event: AnalyticsEvent) => {
      if (!isMountedRef.current) return;

      setStatus((prev) => ({
        ...prev,
        lastUpdate: new Date(),
        eventCount: prev.eventCount + 1,
      }));

      // Invalidate relevant queries based on event type
      if (event.type === 'summary_update') {
        queryClient.invalidateQueries({ queryKey: ['analytics', 'summary'] });
      } else if (event.type === 'artifact_update') {
        queryClient.invalidateQueries({ queryKey: ['analytics', 'top-artifacts'] });
      } else if (event.type === 'trend_update') {
        queryClient.invalidateQueries({ queryKey: ['analytics', 'trends'] });
      }

      // Call custom event handler if provided
      onEvent?.(event);
    },
    [queryClient, onEvent]
  );

  /**
   * Try to establish SSE connection
   */
  const connectSSE = useCallback(() => {
    if (!enabled || !isMountedRef.current) return;

    const sseUrl = `${API_BASE_URL}/api/${API_VERSION}/analytics/stream`;

    setStatus((prev) => ({ ...prev, isConnecting: true, error: null }));

    try {
      const eventSource = new EventSource(`${sseUrl}?api_key=${API_KEY}`);

      eventSource.onopen = () => {
        if (!isMountedRef.current) return;

        setStatus((prev) => ({
          ...prev,
          isConnected: true,
          isConnecting: false,
          error: null,
        }));

        onConnect?.();
      };

      eventSource.onmessage = (event) => {
        if (!isMountedRef.current) return;

        try {
          const analyticsEvent: AnalyticsEvent = JSON.parse(event.data);
          handleEvent(analyticsEvent);
        } catch (err) {
          console.error('Failed to parse SSE event:', err);
        }
      };

      eventSource.onerror = () => {
        if (!isMountedRef.current) return;

        const errorObj = new Error('SSE connection error');

        setStatus((prev) => ({
          ...prev,
          isConnected: false,
          isConnecting: false,
          error: errorObj,
        }));

        onError?.(errorObj);
        eventSource.close();

        // Try to reconnect after delay
        reconnectTimeoutRef.current = setTimeout(() => {
          if (isMountedRef.current) {
            connectSSE();
          }
        }, 5000);
      };

      eventSourceRef.current = eventSource;
    } catch (error) {
      // SSE not available, fall back to polling
      console.log('SSE not available, using polling fallback');
      startPolling();
    }
  }, [enabled, handleEvent, onConnect, onError]);

  /**
   * Start polling as fallback
   */
  const startPolling = useCallback(() => {
    if (!enabled || pollingIntervalRef.current || !isMountedRef.current) return;

    setStatus((prev) => ({
      ...prev,
      isConnected: true,
      isConnecting: false,
      error: null,
    }));

    onConnect?.();

    // Poll every 30 seconds
    pollingIntervalRef.current = setInterval(() => {
      if (!isMountedRef.current) return;

      // Trigger query invalidation to simulate updates
      queryClient.invalidateQueries({ queryKey: ['analytics'] });

      setStatus((prev) => ({
        ...prev,
        lastUpdate: new Date(),
        eventCount: prev.eventCount + 1,
      }));
    }, 30000);
  }, [enabled, queryClient, onConnect]);

  /**
   * Disconnect from stream
   */
  const disconnect = useCallback(() => {
    // Close SSE connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }

    // Clear polling
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
    }

    // Clear reconnect timeout
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (isMountedRef.current) {
      setStatus({
        isConnected: false,
        isConnecting: false,
        error: null,
        lastUpdate: null,
        eventCount: 0,
      });

      onDisconnect?.();
    }
  }, [onDisconnect]);

  /**
   * Reconnect to stream
   */
  const reconnect = useCallback(() => {
    disconnect();
    connectSSE();
  }, [disconnect, connectSSE]);

  // Setup and cleanup
  useEffect(() => {
    isMountedRef.current = true;

    if (enabled) {
      // Use polling until SSE endpoint is implemented
      // TODO: Re-enable SSE once /api/v1/analytics/stream endpoint is added
      startPolling();
    }

    return () => {
      isMountedRef.current = false;
      disconnect();
    };
  }, [enabled, startPolling, disconnect]);

  return {
    status,
    reconnect,
    disconnect,
  };
}
