'use client';

import * as React from 'react';
import { useEffect } from 'react';
import { cn } from '@/lib/utils';
import {
  Clock,
  Loader2,
  CheckCircle2,
  XCircle,
  Ban,
  Pause,
  Lock,
  LucideIcon,
} from 'lucide-react';

export type ExecutionStatus =
  | 'pending'
  | 'running'
  | 'completed'
  | 'failed'
  | 'cancelled'
  | 'paused'
  | 'waiting';

export interface StageTimelineItem {
  id: string;
  name: string;
  status: ExecutionStatus;
  duration?: string;
  elapsed?: string;
}

interface StageTimelineProps {
  stages: StageTimelineItem[];
  selectedStageId: string | null;
  onSelectStage: (id: string) => void;
}

const statusConfig: Record<
  ExecutionStatus,
  { className: string; Icon: LucideIcon }
> = {
  pending: {
    className: 'border-muted bg-muted/50 text-muted-foreground',
    Icon: Clock,
  },
  running: {
    className: 'border-blue-500 bg-blue-50 text-blue-600',
    Icon: Loader2,
  },
  completed: {
    className: 'border-green-500 bg-green-50 text-green-600',
    Icon: CheckCircle2,
  },
  failed: {
    className: 'border-red-500 bg-red-50 text-red-600',
    Icon: XCircle,
  },
  cancelled: {
    className: 'border-amber-500 bg-amber-50 text-amber-700',
    Icon: Ban,
  },
  paused: {
    className: 'border-yellow-500 bg-yellow-50 text-yellow-700',
    Icon: Pause,
  },
  waiting: {
    className: 'border-indigo-500 bg-indigo-50 text-indigo-600',
    Icon: Lock,
  },
};

const getStatusSubtext = (stage: StageTimelineItem): string => {
  switch (stage.status) {
    case 'running':
      return `running (${stage.elapsed || '...'})`;
    case 'completed':
      return `completed (${stage.duration || '...'})`;
    case 'failed':
      return `failed (${stage.duration || '...'})`;
    default:
      return stage.status;
  }
};

export function StageTimeline({
  stages,
  selectedStageId,
  onSelectStage,
}: StageTimelineProps) {
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key !== 'j' && event.key !== 'k') {
        return;
      }

      event.preventDefault();
      const currentIndex = stages.findIndex(
        (stage) => stage.id === selectedStageId
      );

      let nextIndex = -1;
      if (event.key === 'j') {
        // Move down
        nextIndex = currentIndex < stages.length - 1 ? currentIndex + 1 : 0;
      } else if (event.key === 'k') {
        // Move up
        nextIndex = currentIndex > 0 ? currentIndex - 1 : stages.length - 1;
      }

      if (
        nextIndex !== -1 &&
        stages[nextIndex] &&
        stages[nextIndex].id !== selectedStageId
      ) {
        onSelectStage(stages[nextIndex].id);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [stages, selectedStageId, onSelectStage]);

  return (
    <div className='w-full h-full overflow-y-auto p-4 space-y-0'>
      <ul role='list'>
        {stages.map((stage, index) => {
          const isLast = index === stages.length - 1;
          const isSelected = stage.id === selectedStageId;
          const config = statusConfig[stage.status];
          const Icon = config.Icon;

          return (
            <li
              key={stage.id}
              role='listitem'
              className='flex items-start gap-3'
              aria-current={stage.status === 'running' ? 'step' : undefined}
            >
              <div className='flex flex-col items-center'>
                <div
                  className={cn(
                    'h-8 w-8 rounded-full border-2 flex items-center justify-center',
                    config.className
                  )}
                >
                  <Icon
                    className={cn(
                      'h-4 w-4',
                      stage.status === 'running' && 'animate-spin'
                    )}
                  />
                </div>
                <div
                  className={cn(
                    'h-8 w-px bg-border',
                    isLast && 'invisible'
                  )}
                />
              </div>

              <button
                onClick={() => onSelectStage(stage.id)}
                aria-selected={isSelected}
                className={cn(
                  'flex-1 rounded-md px-3 py-2 text-left text-sm transition-colors hover:bg-accent/50 -mt-1',
                  isSelected && 'bg-accent'
                )}
              >
                <div className='font-medium'>{stage.name}</div>
                <div className='text-xs text-muted-foreground mt-0.5'>
                  {getStatusSubtext(stage)}
                </div>
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
