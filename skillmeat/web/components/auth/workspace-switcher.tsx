'use client';

import { useState } from 'react';
import { ChevronDown, Check, Building2, User } from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Button } from '@/components/ui/button';
import { useAuth, useAuthUser } from '@/lib/auth';

/** Derives up to 2 uppercase initials from a name string. */
function getInitials(name: string | null): string {
  if (!name) return '?';
  const parts = name.trim().split(/\s+/);
  const first = parts[0] || '';
  if (parts.length === 1) return first.slice(0, 2).toUpperCase();
  const last = parts[parts.length - 1] || '';
  return ((first.charAt(0)) + (last.charAt(0))).toUpperCase() || '?';
}

/** Small circular avatar that shows an image or falls back to initials. */
function WorkspaceAvatar({
  imageUrl,
  name,
  size = 'sm',
}: {
  imageUrl: string | null;
  name: string | null;
  size?: 'sm' | 'xs';
}) {
  const sizeClasses = size === 'xs' ? 'h-5 w-5 text-[10px]' : 'h-6 w-6 text-xs';

  if (imageUrl) {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img
        src={imageUrl}
        alt={name ?? 'Workspace avatar'}
        className={`${sizeClasses} rounded-full object-cover flex-shrink-0`}
      />
    );
  }

  return (
    <span
      aria-hidden="true"
      className={`${sizeClasses} rounded-full bg-muted flex items-center justify-center font-medium text-muted-foreground flex-shrink-0 select-none`}
    >
      {getInitials(name)}
    </span>
  );
}

/** Resolves the display name for the current workspace. */
function getCurrentWorkspaceName(
  organizationId: string | null,
  organizations: Array<{ id: string; name: string; role: string }>,
  userName: string | null,
): string {
  if (!organizationId) return userName ?? 'Personal';
  const org = organizations.find((o) => o.id === organizationId);
  return org?.name ?? 'Personal';
}

/**
 * WorkspaceSwitcher — header dropdown for switching between personal workspace
 * and team workspaces. Renders nothing when auth is disabled (zero-auth mode).
 */
export function WorkspaceSwitcher() {
  const auth = useAuth();
  const user = useAuthUser();
  const [isSwitching, setIsSwitching] = useState(false);

  // Zero-auth mode: no multi-tenant concept, hide entirely
  if (!auth.isEnabled || !user) return null;

  const { organizationId, organizations, name, imageUrl } = user;
  const currentWorkspaceName = getCurrentWorkspaceName(organizationId, organizations, name);
  const isPersonal = organizationId === null;

  async function handleSwitch(targetOrgId: string | null) {
    // No-op if already on the selected workspace
    if (targetOrgId === organizationId) return;

    setIsSwitching(true);
    try {
      await auth.switchOrganization(targetOrgId ?? '');
    } finally {
      setIsSwitching(false);
    }
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          className="flex items-center gap-2 h-8 px-2 text-sm font-medium max-w-[200px]"
          aria-label={`Current workspace: ${currentWorkspaceName}. Click to switch workspace.`}
          disabled={isSwitching}
        >
          {isPersonal ? (
            <User className="h-4 w-4 flex-shrink-0 text-muted-foreground" aria-hidden="true" />
          ) : (
            <Building2
              className="h-4 w-4 flex-shrink-0 text-muted-foreground"
              aria-hidden="true"
            />
          )}
          <span className="truncate">{currentWorkspaceName}</span>
          <ChevronDown
            className="h-3 w-3 flex-shrink-0 text-muted-foreground"
            aria-hidden="true"
          />
        </Button>
      </DropdownMenuTrigger>

      <DropdownMenuContent align="end" className="w-56" role="menu">
        <DropdownMenuLabel className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
          Workspaces
        </DropdownMenuLabel>
        <DropdownMenuSeparator />

        {/* Personal workspace */}
        <DropdownMenuItem
          role="menuitem"
          aria-current={isPersonal ? 'true' : undefined}
          className="flex items-center gap-2 cursor-pointer"
          onSelect={() => handleSwitch(null)}
        >
          <WorkspaceAvatar imageUrl={imageUrl} name={name} size="xs" />
          <span className="flex-1 truncate">{name ?? 'Personal'}</span>
          {isPersonal && (
            <Check className="h-3.5 w-3.5 text-foreground flex-shrink-0" aria-hidden="true" />
          )}
        </DropdownMenuItem>

        {/* Team workspaces */}
        {organizations.length > 0 && (
          <>
            <DropdownMenuSeparator />
            {organizations.map((org) => {
              const isActive = organizationId === org.id;
              return (
                <DropdownMenuItem
                  key={org.id}
                  role="menuitem"
                  aria-current={isActive ? 'true' : undefined}
                  className="flex items-center gap-2 cursor-pointer"
                  onSelect={() => handleSwitch(org.id)}
                >
                  <span
                    aria-hidden="true"
                    className="h-5 w-5 rounded-full bg-muted flex items-center justify-center text-[10px] font-medium text-muted-foreground flex-shrink-0 select-none"
                  >
                    {getInitials(org.name)}
                  </span>
                  <span className="flex-1 truncate">{org.name}</span>
                  {isActive && (
                    <Check
                      className="h-3.5 w-3.5 text-foreground flex-shrink-0"
                      aria-hidden="true"
                    />
                  )}
                </DropdownMenuItem>
              );
            })}
          </>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
