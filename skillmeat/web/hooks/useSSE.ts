/**
 * Server-Sent Events (SSE) hook for real-time progress updates
 */

import { useState, useEffect, useCallback } from 'react';

export interface SSEMessage<T = any> {
  event: string;
  data: T;
}

export interface SSEState<T = any> {
  isConnected: boolean;
  isConnecting: boolean;
  error: Error | null;
  messages: SSEMessage<T>[];
  lastMessage: SSEMessage<T> | null;
}

export interface UseSSEOptions {
  enabled?: boolean;
  onMessage?: (message: SSEMessage) => void;
  onError?: (error: Error) => void;
  onOpen?: () => void;
  onClose?: () => void;
}

export function useSSE<T = any>(url: string | null, options: UseSSEOptions = {}) {
  const [state, setState] = useState<SSEState<T>>({
    isConnected: false,
    isConnecting: false,
    error: null,
    messages: [],
    lastMessage: null,
  });

  const connect = useCallback(() => {
    // TODO: Implement full SSE logic from DEPLOY_SYNC_UI_IMPLEMENTATION.md
    setState((prev) => ({ ...prev, isConnecting: true }));
  }, []);

  const disconnect = useCallback(() => {
    setState((prev) => ({ ...prev, isConnected: false }));
    options.onClose?.();
  }, [options]);

  const clearMessages = useCallback(() => {
    setState((prev) => ({ ...prev, messages: [], lastMessage: null }));
  }, []);

  useEffect(() => {
    if (options.enabled && url) {
      connect();
    }
    return () => disconnect();
  }, [url, options.enabled, connect, disconnect]);

  return {
    ...state,
    connect,
    disconnect,
    clearMessages,
  };
}
