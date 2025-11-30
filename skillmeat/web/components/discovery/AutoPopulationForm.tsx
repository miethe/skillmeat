/**
 * Auto-Population Form Component
 *
 * A form component that auto-populates artifact metadata from a GitHub URL.
 * Users can quickly add artifacts by providing a GitHub source, which automatically
 * fetches and populates metadata fields like name, description, author, and tags.
 *
 * Features:
 * - Debounced GitHub metadata fetching (500ms delay)
 * - Auto-population of name, description, author, and tags
 * - Editable fields after auto-population
 * - Loading states with skeleton and spinner
 * - Error handling with Alert component
 * - Form validation before submission
 * - Scope selection (user/local)
 *
 * @example
 * ```tsx
 * <AutoPopulationForm
 *   artifactType="skill"
 *   onImport={async (artifact) => {
 *     await createArtifact(artifact);
 *   }}
 *   onCancel={() => setShowForm(false)}
 * />
 * ```
 */

'use client';

import { useState, useEffect } from 'react';
import { useDebouncedCallback } from 'use-debounce';
import { Loader2, AlertCircle, CheckCircle2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import type { ArtifactCreateRequest } from '@/sdk';

interface GitHubMetadata {
  title?: string;
  description?: string;
  author?: string;
  license?: string;
  topics: string[];
  url: string;
  fetched_at: string;
}

export interface AutoPopulationFormProps {
  /** Type of artifact being created */
  artifactType: string;
  /** Callback when user submits the form */
  onImport: (artifact: ArtifactCreateRequest) => Promise<void>;
  /** Optional callback when user cancels */
  onCancel?: () => void;
}

export function AutoPopulationForm({
  artifactType,
  onImport,
  onCancel,
}: AutoPopulationFormProps) {
  const [source, setSource] = useState('');
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [author, setAuthor] = useState('');
  const [tags, setTags] = useState('');
  const [scope, setScope] = useState<'user' | 'local'>('user');

  const [isLoading, setIsLoading] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [metadata, setMetadata] = useState<GitHubMetadata | null>(null);

  // Debounced fetch when source changes
  const fetchMetadata = useDebouncedCallback(async (sourceValue: string) => {
    if (!sourceValue || !sourceValue.includes('/')) {
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(
        `/api/v1/artifacts/metadata/github?source=${encodeURIComponent(sourceValue)}`
      );
      const data = await response.json();

      if (data.success && data.metadata) {
        setMetadata(data.metadata);
        // Auto-populate fields if empty
        if (!name) setName(data.metadata.title || '');
        if (!description) setDescription(data.metadata.description || '');
        if (!author) setAuthor(data.metadata.author || '');
        if (!tags) setTags(data.metadata.topics?.join(', ') || '');
      } else {
        setError(data.error || 'Failed to fetch metadata');
      }
    } catch (err) {
      setError('Network error fetching metadata');
    } finally {
      setIsLoading(false);
    }
  }, 500);

  const handleSourceChange = (value: string) => {
    setSource(value);
    fetchMetadata(value);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    try {
      await onImport({
        source_type: 'github',
        source,
        artifact_type: artifactType,
        name: name || undefined,
        description: description || undefined,
        tags: tags ? tags.split(',').map((t) => t.trim()).filter(Boolean) : undefined,
        collection: scope,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Import failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {/* GitHub Source */}
      <div className="space-y-2">
        <Label htmlFor="source">
          GitHub Source <span className="text-destructive">*</span>
        </Label>
        <div className="relative">
          <Input
            id="source"
            placeholder="user/repo/path or https://github.com/..."
            value={source}
            onChange={(e) => handleSourceChange(e.target.value)}
            disabled={isSubmitting}
            aria-describedby="source-hint"
          />
          {isLoading && (
            <Loader2 className="absolute right-3 top-2.5 h-4 w-4 animate-spin text-muted-foreground" />
          )}
        </div>
        <p id="source-hint" className="text-sm text-muted-foreground">
          Enter a GitHub repository path or URL
        </p>
        {metadata && (
          <p className="text-sm text-green-600 flex items-center gap-1">
            <CheckCircle2 className="h-3 w-3" aria-hidden="true" />
            Metadata fetched successfully
          </p>
        )}
      </div>

      {/* Error Alert */}
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Loading Skeleton */}
      {isLoading && (
        <div className="space-y-4">
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-10 w-full" />
        </div>
      )}

      {/* Auto-populated fields */}
      {!isLoading && (
        <>
          <div className="space-y-2">
            <Label htmlFor="name">Name</Label>
            <Input
              id="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Artifact name"
              disabled={isSubmitting}
            />
            <p className="text-sm text-muted-foreground">
              Override the artifact name (optional)
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Artifact description"
              rows={3}
              disabled={isSubmitting}
            />
            <p className="text-sm text-muted-foreground">
              Override the artifact description (optional)
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="author">Author</Label>
            <Input
              id="author"
              value={author}
              onChange={(e) => setAuthor(e.target.value)}
              placeholder="Author name"
              disabled={isSubmitting}
            />
            <p className="text-sm text-muted-foreground">
              Override the author name (optional)
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="tags">Tags</Label>
            <Input
              id="tags"
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              placeholder="Comma-separated tags"
              disabled={isSubmitting}
            />
            <p className="text-sm text-muted-foreground">
              Add custom tags (optional, comma-separated)
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="scope">Scope</Label>
            <Select
              value={scope}
              onValueChange={(value) => setScope(value as 'user' | 'local')}
              disabled={isSubmitting}
            >
              <SelectTrigger id="scope">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="user">User (Global)</SelectItem>
                <SelectItem value="local">Local (Project)</SelectItem>
              </SelectContent>
            </Select>
            <p className="text-sm text-muted-foreground">
              Choose where to store the artifact
            </p>
          </div>
        </>
      )}

      {/* Actions */}
      <div className="flex gap-2 justify-end pt-4">
        {onCancel && (
          <Button
            type="button"
            variant="outline"
            onClick={onCancel}
            disabled={isSubmitting}
          >
            Cancel
          </Button>
        )}
        <Button type="submit" disabled={!source || isLoading || isSubmitting}>
          {isSubmitting ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Importing...
            </>
          ) : (
            'Import'
          )}
        </Button>
      </div>
    </form>
  );
}
