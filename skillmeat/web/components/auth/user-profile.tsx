'use client';

import React, { useState } from 'react';
import { LogOut, Building2, User, ShieldCheck, Wifi, WifiOff } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { useAuth, useAuthUser } from '@/lib/auth';

/** Derives up to 2 uppercase initials from a name string. */
function getInitials(name: string | null): string {
  if (!name) return '?';
  const parts = name.trim().split(/\s+/);
  const first = parts[0] || '';
  if (parts.length === 1) return first.slice(0, 2).toUpperCase();
  const last = parts[parts.length - 1] || '';
  return (first.charAt(0) + last.charAt(0)).toUpperCase() || '?';
}

/** Maps a role string to a human-readable label. */
function roleLabel(role: string): string {
  switch (role) {
    case 'system_admin':
      return 'System Admin';
    case 'admin':
      return 'Admin';
    case 'member':
      return 'Member';
    case 'viewer':
      return 'Viewer';
    default:
      return role.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
  }
}

/** Avatar circle — image with initials fallback. */
function UserAvatar({ imageUrl, name, size = 'lg' }: { imageUrl: string | null; name: string | null; size?: 'sm' | 'lg' }) {
  const sizeClasses =
    size === 'lg' ? 'h-14 w-14 text-xl' : 'h-8 w-8 text-sm';

  if (imageUrl) {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img
        src={imageUrl}
        alt={name ?? 'User avatar'}
        className={`${sizeClasses} rounded-full object-cover flex-shrink-0`}
      />
    );
  }

  return (
    <span
      aria-hidden="true"
      className={`${sizeClasses} rounded-full bg-muted flex items-center justify-center font-semibold text-muted-foreground flex-shrink-0 select-none`}
    >
      {getInitials(name)}
    </span>
  );
}

/**
 * UserProfile — displays current user info, organizations/teams with roles,
 * and a sign-out button.
 *
 * In zero-auth mode (auth.isEnabled === false) it renders a "Local Mode"
 * indicator instead of showing live identity data or a sign-out button.
 */
export function UserProfile() {
  const auth = useAuth();
  const user = useAuthUser();
  const [isSigningOut, setIsSigningOut] = useState(false);

  async function handleSignOut() {
    setIsSigningOut(true);
    try {
      await auth.signOut();
    } finally {
      setIsSigningOut(false);
    }
  }

  // ── Local / zero-auth mode ──────────────────────────────────────────────
  if (!auth.isEnabled) {
    return (
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <User className="h-5 w-5" />
            <CardTitle>Account</CardTitle>
          </div>
          <CardDescription>Your identity and workspace settings</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-3 rounded-lg border border-dashed p-4 text-muted-foreground">
            <WifiOff className="h-5 w-5 flex-shrink-0" aria-hidden="true" />
            <div>
              <p className="text-sm font-medium text-foreground">Local Mode</p>
              <p className="text-xs">
                Authentication is disabled. SkillMeat is running in single-user local mode.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  // ── Auth enabled but no user (shouldn't happen in normal flows) ─────────
  if (!user) {
    return (
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <User className="h-5 w-5" />
            <CardTitle>Account</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">Not signed in.</p>
        </CardContent>
      </Card>
    );
  }

  const { name, email, imageUrl, organizationId, organizations } = user;
  const activeOrg = organizations.find((o) => o.id === organizationId) ?? null;

  // ── Authenticated view ──────────────────────────────────────────────────
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <User className="h-5 w-5" />
          <CardTitle>Account</CardTitle>
        </div>
        <CardDescription>Your identity and workspace settings</CardDescription>
      </CardHeader>

      <CardContent className="space-y-6">
        {/* Identity row */}
        <section aria-label="User identity">
          <div className="flex items-center gap-4">
            <UserAvatar imageUrl={imageUrl} name={name} size="lg" />
            <div className="min-w-0">
              <p className="text-base font-semibold leading-tight truncate" title={name ?? undefined}>
                {name ?? 'Unknown user'}
              </p>
              {email && (
                <p className="text-sm text-muted-foreground truncate" title={email}>
                  {email}
                </p>
              )}
              <div className="flex items-center gap-1.5 mt-1">
                <Wifi className="h-3 w-3 text-green-500" aria-hidden="true" />
                <span className="text-xs text-muted-foreground">Authenticated</span>
              </div>
            </div>
          </div>
        </section>

        <Separator />

        {/* Active workspace */}
        <section aria-label="Active workspace">
          <h3 className="text-sm font-medium mb-3">Active Workspace</h3>
          <div className="flex items-center gap-3 rounded-md border p-3">
            {activeOrg ? (
              <Building2 className="h-4 w-4 flex-shrink-0 text-muted-foreground" aria-hidden="true" />
            ) : (
              <User className="h-4 w-4 flex-shrink-0 text-muted-foreground" aria-hidden="true" />
            )}
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">
                {activeOrg ? activeOrg.name : (name ?? 'Personal')}
              </p>
              <p className="text-xs text-muted-foreground">
                {activeOrg ? 'Team workspace' : 'Personal workspace'}
              </p>
            </div>
            {activeOrg && (
              <Badge variant="secondary" className="flex-shrink-0 text-xs">
                {roleLabel(activeOrg.role)}
              </Badge>
            )}
          </div>
        </section>

        {/* Organizations / teams list */}
        {organizations.length > 0 && (
          <>
            <Separator />
            <section aria-label="Organizations and teams">
              <h3 className="text-sm font-medium mb-3">
                Organizations &amp; Teams
                <span className="ml-1.5 text-muted-foreground font-normal">
                  ({organizations.length})
                </span>
              </h3>
              <ul role="list" className="space-y-2">
                {organizations.map((org) => {
                  const isActive = org.id === organizationId;
                  return (
                    <li
                      key={org.id}
                      role="listitem"
                      className="flex items-center gap-3 rounded-md border p-3"
                    >
                      <span
                        aria-hidden="true"
                        className="h-7 w-7 rounded-full bg-muted flex items-center justify-center text-xs font-semibold text-muted-foreground flex-shrink-0 select-none"
                      >
                        {getInitials(org.name)}
                      </span>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">{org.name}</p>
                        <div className="flex items-center gap-1.5 mt-0.5">
                          {org.role === 'system_admin' || org.role === 'admin' ? (
                            <ShieldCheck
                              className="h-3 w-3 text-muted-foreground"
                              aria-hidden="true"
                            />
                          ) : null}
                          <span className="text-xs text-muted-foreground">{roleLabel(org.role)}</span>
                        </div>
                      </div>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        {isActive && (
                          <Badge variant="outline" className="text-xs">
                            Active
                          </Badge>
                        )}
                      </div>
                    </li>
                  );
                })}
              </ul>
            </section>
          </>
        )}

        <Separator />

        {/* Sign out */}
        <section aria-label="Session actions">
          <Button
            variant="destructive"
            size="sm"
            onClick={handleSignOut}
            disabled={isSigningOut}
            aria-label="Sign out of SkillMeat"
          >
            <LogOut className="mr-2 h-4 w-4" aria-hidden="true" />
            {isSigningOut ? 'Signing out…' : 'Sign out'}
          </Button>
        </section>
      </CardContent>
    </Card>
  );
}
