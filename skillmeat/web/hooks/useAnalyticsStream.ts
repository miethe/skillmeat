/**
 * Server-Sent Events hook for real-time analytics updates.
 */

import { useEffect, useState, useCallback, useRef } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import type { AnalyticsEvent } from '@/types/analytics';
import { apiConfig } from '@/lib/api';

const API_BASE_URL = apiConfig.baseUrl;
const API_VERSION = apiConfig.version;
const API_KEY = apiConfig.apiKey;

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

  const invalidateAnalytics = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['analytics', 'summary'] });
    queryClient.invalidateQueries({ queryKey: ['analytics', 'enterprise-summary'] });
    queryClient.invalidateQueries({ queryKey: ['analytics', 'top-artifacts'] });
    queryClient.invalidateQueries({ queryKey: ['analytics', 'trends'] });
    queryClient.invalidateQueries({ queryKey: ['analytics', 'events'] });
  }, [queryClient]);

  const handleEvent = useCallback(
    (event: AnalyticsEvent) => {
      if (!isMountedRef.current) return;

      setStatus((prev) => ({
        ...prev,
        lastUpdate: new Date(),
        eventCount: prev.eventCount + 1,
      }));

      invalidateAnalytics();
      onEvent?.(event);
    },
    [invalidateAnalytics, onEvent]
  );

  const startPolling = useCallback(() => {
    if (!enabled || pollingIntervalRef.current || !isMountedRef.current) return;

    setStatus((prev) => ({
      ...prev,
      isConnected: true,
      isConnecting: false,
      error: null,
    }));
    onConnect?.();

    pollingIntervalRef.current = setInterval(() => {
      if (!isMountedRef.current) return;
      invalidateAnalytics();
      setStatus((prev) => ({
        ...prev,
        lastUpdate: new Date(),
        eventCount: prev.eventCount + 1,
      }));
    }, 30000);
  }, [enabled, invalidateAnalytics, onConnect]);

  const connectSSE = useCallback(() => {
    if (!enabled || !isMountedRef.current) return;

    setStatus((prev) => ({ ...prev, isConnecting: true, error: null }));

    try {
      const baseUrl = `${API_BASE_URL}/api/${API_VERSION}/analytics/stream`;
      const params = new URLSearchParams();
      if (API_KEY) {
        params.set('api_key', API_KEY);
      }
      const sseUrl = params.toString() ? `${baseUrl}?${params.toString()}` : baseUrl;

      const eventSource = new EventSource(sseUrl);

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
          // eslint-disable-next-line no-console
          console.error('Failed to parse analytics SSE message', err);
        }
      };

      eventSource.onerror = () => {
        if (!isMountedRef.current) return;
        eventSource.close();
        eventSourceRef.current = null;

        const errorObj = new Error('Analytics stream disconnected');
        setStatus((prev) => ({
          ...prev,
          isConnected: false,
          isConnecting: false,
          error: errorObj,
        }));
        onError?.(errorObj);

        // Keep dashboards live with polling while reconnecting.
        startPolling();
        reconnectTimeoutRef.current = setTimeout(() => {
          if (isMountedRef.current) {
            connectSSE();
          }
        }, 10000);
      };

      eventSourceRef.current = eventSource;
    } catch (error) {
      startPolling();
      const errorObj = error instanceof Error ? error : new Error('Failed to start analytics SSE');
      setStatus((prev) => ({
        ...prev,
        isConnected: false,
        isConnecting: false,
        error: errorObj,
      }));
      onError?.(errorObj);
    }
  }, [enabled, handleEvent, onConnect, onError, startPolling]);

  const disconnect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }

    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
    }

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

  const reconnect = useCallback(() => {
    disconnect();
    connectSSE();
  }, [connectSSE, disconnect]);

  useEffect(() => {
    isMountedRef.current = true;

    if (enabled) {
      connectSSE();
    }

    return () => {
      isMountedRef.current = false;
      disconnect();
    };
  }, [enabled, connectSSE, disconnect]);

  return {
    status,
    reconnect,
    disconnect,
  };
}
