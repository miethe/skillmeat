/**
 * Server-Sent Events (SSE) hook for real-time progress updates
 */

import { useState, useEffect, useCallback, useRef } from 'react';

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

  // Store options in a ref to avoid dependency changes triggering effects
  const optionsRef = useRef(options);
  optionsRef.current = options;

  // Track if we're currently connected to avoid state updates after unmount
  const isConnectedRef = useRef(false);

  const connect = useCallback(() => {
    // TODO: Implement full SSE logic from DEPLOY_SYNC_UI_IMPLEMENTATION.md
    setState((prev) => ({ ...prev, isConnecting: true }));
    isConnectedRef.current = true;
  }, []);

  const disconnect = useCallback(() => {
    // Only update state if we were actually connected
    if (isConnectedRef.current) {
      isConnectedRef.current = false;
      setState((prev) => ({ ...prev, isConnected: false, isConnecting: false }));
      optionsRef.current.onClose?.();
    }
  }, []); // No dependencies - uses refs

  const clearMessages = useCallback(() => {
    setState((prev) => ({ ...prev, messages: [], lastMessage: null }));
  }, []);

  // Effect to manage connection lifecycle
  // Only depends on url and enabled, not on callbacks
  useEffect(() => {
    const { enabled } = optionsRef.current;

    if (enabled && url) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [url, options.enabled, connect, disconnect]);

  return {
    ...state,
    connect,
    disconnect,
    clearMessages,
  };
}
