'use client';

import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { Platform } from '@/types/enums';
import { Bot, Cpu, Sparkles, MousePointerClick, CircleDot } from 'lucide-react';

interface PlatformConfig {
  label: string;
  className: string;
  Icon: typeof Bot;
}

const PLATFORM_CONFIG: Record<string, PlatformConfig> = {
  [Platform.CLAUDE_CODE]: {
    label: 'Claude',
    className: 'border-indigo-500/20 bg-indigo-500/10 text-indigo-700 dark:text-indigo-300',
    Icon: Bot,
  },
  [Platform.CODEX]: {
    label: 'Codex',
    className: 'border-sky-500/20 bg-sky-500/10 text-sky-700 dark:text-sky-300',
    Icon: Cpu,
  },
  [Platform.GEMINI]: {
    label: 'Gemini',
    className:
      'border-emerald-500/20 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300',
    Icon: Sparkles,
  },
  [Platform.CURSOR]: {
    label: 'Cursor',
    className:
      'border-amber-500/20 bg-amber-500/10 text-amber-700 dark:text-amber-300',
    Icon: MousePointerClick,
  },
  [Platform.OTHER]: {
    label: 'Other',
    className: 'border-muted-foreground/20 bg-muted text-muted-foreground',
    Icon: CircleDot,
  },
};

export interface PlatformBadgeProps {
  platform?: Platform | string | null;
  className?: string;
  compact?: boolean;
}

export function PlatformBadge({ platform, className, compact = false }: PlatformBadgeProps) {
  const key = platform ? String(platform) : Platform.OTHER;
  const config = PLATFORM_CONFIG[key] || PLATFORM_CONFIG[Platform.OTHER];
  const Icon = config.Icon;

  return (
    <Badge
      variant="outline"
      className={cn(
        'inline-flex items-center gap-1 font-medium',
        compact ? 'px-1.5 py-0 text-[10px]' : 'px-2 py-0.5 text-xs',
        config.className,
        className
      )}
    >
      <Icon className={compact ? 'h-3 w-3' : 'h-3.5 w-3.5'} />
      <span>{config.label}</span>
    </Badge>
  );
}
