'use client';

import * as React from 'react';
import { 
  Clock, 
  Loader2, 
  CheckCircle2, 
  XCircle, 
  Ban, 
  Pause, 
  Lock 
} from 'lucide-react';
import { cn } from '@skillmeat/web/lib/utils';

export type ExecutionStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled' | 'paused' | 'waiting';

export interface StageTimelineItem {
  id: string;
  name: string;
  status: ExecutionStatus;
  duration?: string;
  elapsed?: string;
}

export interface StageTimelineProps {
  stages: StageTimelineItem[];
  selectedStageId: string | null;
  onSelectStage: (id: string) => void;
}

const statusConfig = {
  pending: {
    icon: Clock,
    circleClass: 'border-muted bg-muted/50 text-muted-foreground',
    iconClass: '',
  },
  running: {
    icon: Loader2,
    circleClass: 'border-blue-500 bg-blue-50 text-blue-600',
    iconClass: 'animate-spin',
  },
  completed: {
    icon: CheckCircle2,
    circleClass: 'border-green-500 bg-green-50 text-green-600',
    iconClass: '',
  },
  failed: {
    icon: XCircle,
    circleClass: 'border-red-500 bg-red-50 text-red-600',
    iconClass: '',
  },
  cancelled: {
    icon: Ban,
    circleClass: 'border-amber-500 bg-amber-50 text-amber-700',
    iconClass: '',
  },
  paused: {
    icon: Pause,
    circleClass: 'border-yellow-500 bg-yellow-50 text-yellow-700',
    iconClass: '',
  },
  waiting: {
    icon: Lock,
    circleClass: 'border-indigo-500 bg-indigo-50 text-indigo-600',
    iconClass: '',
  },
};

export function StageTimeline({ stages, selectedStageId, onSelectStage }: StageTimelineProps) {
  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (stages.length === 0) return;

      const target = e.target as HTMLElement;
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable) {
        return;
      }

      if (e.key === 'j') {
        const currentIndex = stages.findIndex((s) => s.id === selectedStageId);
        const nextIndex = currentIndex === -1 ? 0 : (currentIndex + 1) % stages.length;
        onSelectStage(stages[nextIndex].id);
      } else if (e.key === 'k') {
        const currentIndex = stages.findIndex((s) => s.id === selectedStageId);
        const prevIndex = currentIndex === -1 ? stages.length - 1 : (currentIndex - 1 + stages.length) % stages.length;
        onSelectStage(stages[prevIndex].id);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [stages, selectedStageId, onSelectStage]);

  return (
    <div className="w-full h-full overflow-y-auto p-4">
      <div role="list" className="flex flex-col">
        {stages.map((stage, index) => {
          const config = statusConfig[stage.status];
          const Icon = config.icon;
          const isSelected = stage.id === selectedStageId;
          const isLast = index === stages.length - 1;

          return (
            <div key={stage.id} role="listitem" className="flex items-start gap-3">
              <div className="flex flex-col items-center">
                <div 
                  className={cn(
                    "h-8 w-8 rounded-full border-2 flex items-center justify-center transition-colors shrink-0",
                    config.circleClass
                  )}
                >
                  <Icon className={cn("h-4 w-4", config.iconClass)} />
                </div>
                <div 
                  className={cn(
                    "h-8 w-px bg-border",
                    isLast && "invisible"
                  )} 
                />
              </div>
              
              <button
                onClick={() => onSelectStage(stage.id)}
                aria-selected={isSelected}
                aria-current={stage.status === 'running' ? 'step' : undefined}
                className={cn(
                  "flex-1 rounded-md px-3 py-2 text-left text-sm transition-colors mt-0.5 group",
                  isSelected ? "bg-accent text-accent-foreground" : "hover:bg-accent/50 text-foreground"
                )}
              >
                <div className="flex justify-between items-center gap-2">
                  <span className="font-medium truncate">{stage.name}</span>
                  {(stage.elapsed || stage.duration) && (
                    <span className="text-[10px] text-muted-foreground uppercase tabular-nums">
                      {stage.elapsed || stage.duration}
                    </span>
                  )}
                </div>
                <div className="text-xs text-muted-foreground capitalize mt-0.5">
                  {stage.status}
                </div>
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
