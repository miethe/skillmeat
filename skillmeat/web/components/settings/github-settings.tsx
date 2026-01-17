'use client';

import * as React from 'react';
import { Github, CheckCircle2, XCircle, Loader2, Eye, EyeOff } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { cn } from '@/lib/utils';
import { useToast } from '@/hooks';
import {
  getGitHubTokenStatus,
  validateGitHubToken,
  setGitHubToken,
  clearGitHubToken,
  type GitHubTokenStatus,
} from '@/lib/api/settings';

/**
 * GitHubSettings - Manage GitHub Personal Access Token
 *
 * Allows users to set a GitHub PAT to increase API rate limits from 60 req/hr
 * to 5000 req/hr. Validates token format and permissions before saving.
 *
 * States:
 * - Loading: Fetching initial status
 * - Token Set: Shows masked token and username with clear button
 * - Token Not Set: Shows input form with validation
 */
export function GitHubSettings() {
  const { toast } = useToast();
  const [status, setStatus] = React.useState<GitHubTokenStatus | null>(null);
  const [isLoading, setIsLoading] = React.useState(true);
  const [isSubmitting, setIsSubmitting] = React.useState(false);
  const [token, setToken] = React.useState('');
  const [showToken, setShowToken] = React.useState(false);
  const [validationError, setValidationError] = React.useState<string | null>(null);

  // Fetch initial token status
  React.useEffect(() => {
    async function fetchStatus() {
      try {
        const result = await getGitHubTokenStatus();
        setStatus(result);
      } catch (error) {
        toast({
          title: 'Error',
          description: error instanceof Error ? error.message : 'Failed to fetch token status',
          variant: 'destructive',
        });
      } finally {
        setIsLoading(false);
      }
    }
    fetchStatus();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Only run on mount - toast is stable enough for error handling

  // Client-side token format validation
  const isValidTokenFormat = (value: string): boolean => {
    return value.startsWith('ghp_') || value.startsWith('github_pat_');
  };

  // Handle token input change
  const handleTokenChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setToken(value);

    // Clear validation error when user starts typing
    if (validationError) {
      setValidationError(null);
    }
  };

  // Handle setting the token
  const handleSetToken = async () => {
    // Validate format first
    if (!isValidTokenFormat(token)) {
      setValidationError('Token must start with ghp_ or github_pat_');
      return;
    }

    setIsSubmitting(true);
    setValidationError(null);

    try {
      // Validate token with GitHub
      const validation = await validateGitHubToken(token);

      if (!validation.valid) {
        setValidationError('Invalid token. Please check and try again.');
        return;
      }

      // Token is valid, save it
      await setGitHubToken(token);

      // Refresh status
      const newStatus = await getGitHubTokenStatus();
      setStatus(newStatus);
      setToken('');

      toast({
        title: 'Token saved',
        description: `Authenticated as ${validation.username}. Rate limit: ${validation.rate_limit?.toLocaleString()} req/hr`,
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to save token';
      setValidationError(message);
      toast({
        title: 'Error',
        description: message,
        variant: 'destructive',
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  // Handle clearing the token
  const handleClearToken = async () => {
    setIsSubmitting(true);

    try {
      await clearGitHubToken();
      setStatus({ is_set: false });

      toast({
        title: 'Token removed',
        description: 'GitHub token has been cleared. Using unauthenticated access (60 req/hr).',
      });
    } catch (error) {
      toast({
        title: 'Error',
        description: error instanceof Error ? error.message : 'Failed to clear token',
        variant: 'destructive',
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  // Loading state
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Github className="h-5 w-5" />
            <CardTitle>GitHub Integration</CardTitle>
          </div>
          <CardDescription>Loading token status...</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-4">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <Github className="h-5 w-5" />
          <CardTitle>GitHub Integration</CardTitle>
        </div>
        <CardDescription>
          Configure a Personal Access Token to increase API rate limits from 60 to 5,000 requests
          per hour
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {status?.is_set ? (
          // Token is set - show status and clear button
          <div className="space-y-4">
            <div
              className={cn(
                'flex items-start gap-3 rounded-lg border p-4',
                'border-green-500/20 bg-green-500/5'
              )}
            >
              <CheckCircle2 className="mt-0.5 h-5 w-5 flex-shrink-0 text-green-500" />
              <div className="min-w-0 flex-1 space-y-1">
                <p className="font-medium text-green-700 dark:text-green-400">Token configured</p>
                <div className="space-y-0.5 text-sm text-muted-foreground">
                  {status.username && (
                    <p>
                      Authenticated as <span className="font-medium">{status.username}</span>
                    </p>
                  )}
                  {status.masked_token && (
                    <p className="font-mono text-xs">{status.masked_token}</p>
                  )}
                </div>
              </div>
            </div>

            <Button
              variant="destructive"
              onClick={handleClearToken}
              disabled={isSubmitting}
              className="w-full sm:w-auto"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Clearing...
                </>
              ) : (
                'Clear Token'
              )}
            </Button>
          </div>
        ) : (
          // Token not set - show input form
          <div className="space-y-4">
            <div
              className={cn(
                'flex items-start gap-3 rounded-lg border p-4',
                'border-muted bg-muted/30'
              )}
            >
              <XCircle className="mt-0.5 h-5 w-5 flex-shrink-0 text-muted-foreground" />
              <div className="space-y-1">
                <p className="font-medium">No token configured</p>
                <p className="text-sm text-muted-foreground">
                  Using unauthenticated access (60 requests/hour)
                </p>
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="github-token">Personal Access Token</Label>
              <div className="relative">
                <Input
                  id="github-token"
                  type={showToken ? 'text' : 'password'}
                  placeholder="ghp_xxxxxxxxxxxxxxxxxxxx"
                  value={token}
                  onChange={handleTokenChange}
                  disabled={isSubmitting}
                  className={cn('pr-10', validationError && 'border-red-500 focus-visible:ring-red-500')}
                  aria-describedby={validationError ? 'token-error' : 'token-help'}
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="absolute right-0 top-0 h-full px-3 hover:bg-transparent"
                  onClick={() => setShowToken(!showToken)}
                  aria-label={showToken ? 'Hide token' : 'Show token'}
                >
                  {showToken ? (
                    <EyeOff className="h-4 w-4 text-muted-foreground" />
                  ) : (
                    <Eye className="h-4 w-4 text-muted-foreground" />
                  )}
                </Button>
              </div>
              {validationError ? (
                <p id="token-error" className="text-sm text-red-500">
                  {validationError}
                </p>
              ) : (
                <p id="token-help" className="text-sm text-muted-foreground">
                  Token must start with <code className="rounded bg-muted px-1">ghp_</code> or{' '}
                  <code className="rounded bg-muted px-1">github_pat_</code>
                </p>
              )}
            </div>

            <Button
              onClick={handleSetToken}
              disabled={isSubmitting || !token.trim()}
              className="w-full sm:w-auto"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Validating...
                </>
              ) : (
                'Set Token'
              )}
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
