'use client';

import React, { useState, useEffect, useRef } from 'react';
import { ChevronDown, Circle } from 'lucide-react';
import { cn } from '@skillmeat/web/lib/utils.ts';

export type LogLine = {
  id: string;
  timestamp: string;
  level: 'info' | 'warn' | 'error' | 'debug';
  message: string;
};

interface LogViewerProps {
  logs: LogLine[];
  isLive: boolean;
  maxHeight?: string;
}

export function LogViewer({
  logs,
  isLive,
  maxHeight = '400px',
}: LogViewerProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [showScrollButton, setShowScrollButton] = useState(false);

  const checkScroll = () => {
    const container = scrollRef.current;
    if (!container) return;
    
    // Show button if user has scrolled up more than 50px from the bottom
    const isAtBottom = container.scrollHeight - container.scrollTop - container.clientHeight < 50;
    setShowScrollButton(!isAtBottom);
  };

  const scrollToBottom = () => {
    const container = scrollRef.current;
    if (!container) return;
    container.scrollTo({
      top: container.scrollHeight,
      behavior: 'smooth',
    });
  };

  useEffect(() => {
    const container = scrollRef.current;
    if (!container) return;

    const isNearBottom = container.scrollHeight - container.scrollTop - container.clientHeight <= 100;

    if (isLive && isNearBottom) {
      container.scrollTo({
        top: container.scrollHeight,
        behavior: 'smooth',
      });
    }
  }, [logs, isLive]);

  return (
    <div className="rounded-lg border bg-muted/30 p-0 overflow-hidden relative">
      {/* Toolbar */}
      <div className="flex justify-between items-center px-3 py-2 border-b bg-background/50">
        <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
          Logs
        </span>
        <div className="flex items-center gap-2">
          {isLive ? (
            <div className="flex items-center gap-1.5">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                <Circle className="relative inline-flex rounded-full h-2 w-2 fill-green-500 stroke-none" />
              </span>
              <span className="text-[10px] font-bold text-green-600 uppercase tracking-tight">
                Live
              </span>
            </div>
          ) : (
            <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-tight">
              Completed
            </span>
          )}
        </div>
      </div>

      {/* Log Area */}
      <div
        ref={scrollRef}
        onScroll={checkScroll}
        className="overflow-y-auto p-3 space-y-0.5 selection:bg-primary selection:text-primary-foreground"
        style={{ maxHeight }}
      >
        {logs.length === 0 ? (
          <p className="text-xs text-muted-foreground italic">
            Waiting for logs...
          </p>
        ) : (
          logs.map((log) => (
            <p
              key={log.id}
              className={cn(
                "font-mono text-xs leading-relaxed break-all",
                log.level === 'error' && "text-destructive bg-destructive/10 px-1 rounded",
                log.level === 'warn' && "text-yellow-600",
                log.level === 'debug' && "text-muted-foreground",
                log.level === 'info' && "text-foreground"
              )}
            >
              <span className="opacity-50 mr-2">[{log.timestamp}]</span>
              <span>{log.message}</span>
            </p>
          ))
        )}
      </div>

      {/* Scroll to bottom button */}
      {showScrollButton && (
        <button
          onClick={scrollToBottom}
          className="absolute bottom-2 right-2 p-1.5 rounded-full bg-primary text-primary-foreground shadow-lg hover:opacity-90 transition-opacity"
          aria-label="Scroll to bottom"
        >
          <ChevronDown className="h-4 w-4" />
        </button>
      )}
    </div>
  );
}
