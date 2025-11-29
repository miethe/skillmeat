/**
 * Permission Badge Component
 *
 * Visual indicator for permission levels with appropriate styling
 */

import { Badge } from '@/components/ui/badge';
import { Eye, Download, Upload, Shield } from 'lucide-react';
import type { PermissionLevel } from '@/types/bundle';

export interface PermissionBadgeProps {
  level: PermissionLevel;
  showIcon?: boolean;
  className?: string;
}

const permissionConfig: Record<
  PermissionLevel,
  {
    label: string;
    variant: 'default' | 'secondary' | 'destructive' | 'outline';
    icon: typeof Eye;
    description: string;
  }
> = {
  viewer: {
    label: 'Viewer',
    variant: 'outline',
    icon: Eye,
    description: 'Can view bundle contents',
  },
  importer: {
    label: 'Importer',
    variant: 'secondary',
    icon: Download,
    description: 'Can import bundles',
  },
  publisher: {
    label: 'Publisher',
    variant: 'default',
    icon: Upload,
    description: 'Can create and share bundles',
  },
  admin: {
    label: 'Admin',
    variant: 'destructive',
    icon: Shield,
    description: 'Full access and management',
  },
};

export function PermissionBadge({ level, showIcon = true, className }: PermissionBadgeProps) {
  const config = permissionConfig[level];
  const Icon = config.icon;

  return (
    <Badge variant={config.variant} className={className} title={config.description}>
      {showIcon && <Icon className="mr-1 h-3 w-3" />}
      {config.label}
    </Badge>
  );
}

export function PermissionDescription({ level }: { level: PermissionLevel }) {
  const config = permissionConfig[level];
  const Icon = config.icon;

  return (
    <div className="flex items-start gap-2 text-sm">
      <Icon className="mt-0.5 h-4 w-4 text-muted-foreground" />
      <div>
        <p className="font-medium">{config.label}</p>
        <p className="text-xs text-muted-foreground">{config.description}</p>
      </div>
    </div>
  );
}
