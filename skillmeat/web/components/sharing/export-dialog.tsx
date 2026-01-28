'use client';

/**
 * Export Dialog Component
 *
 * Multi-step wizard for exporting artifact bundles
 */

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import {
  Package,
  ChevronRight,
  ChevronLeft,
  Settings,
  Share2,
  CheckCircle,
  Download,
} from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Checkbox } from '@/components/ui/checkbox';
import { ProgressIndicator, ProgressStep } from '../collection/progress-indicator';
import { ShareLink } from './share-link';
import { useArtifacts, useExportBundle } from '@/hooks';
import type {
  ExportRequest,
  BundleMetadata,
  ExportOptions,
  PermissionLevel,
  CompressionLevel,
  BundleFormat,
} from '@/types/bundle';
import type { Artifact } from '@/types/artifact';

export interface ExportDialogProps {
  isOpen: boolean;
  onClose: () => void;
  preselectedArtifacts?: string[];
}

type ExportFormData = {
  artifactIds: string[];
  name: string;
  description: string;
  tags: string;
  license: string;
  author: string;
  version: string;
  includeDependencies: boolean;
  compressionLevel: CompressionLevel;
  format: BundleFormat;
  generateShareLink: boolean;
  linkExpiration: number;
  permissionLevel: PermissionLevel;
};

export function ExportDialog({ isOpen, onClose, preselectedArtifacts = [] }: ExportDialogProps) {
  const [step, setStep] = useState(1);
  const [isExporting, setIsExporting] = useState(false);
  const [streamUrl, setStreamUrl] = useState<string | null>(null);
  const [exportedBundle, setExportedBundle] = useState<any>(null);

  const { data: artifactsData } = useArtifacts();
  const artifacts = artifactsData?.artifacts || [];

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors },
  } = useForm<ExportFormData>({
    defaultValues: {
      artifactIds: preselectedArtifacts,
      name: '',
      description: '',
      tags: '',
      license: 'MIT',
      author: '',
      version: '1.0.0',
      includeDependencies: true,
      compressionLevel: 'balanced',
      format: 'zip',
      generateShareLink: true,
      linkExpiration: 0,
      permissionLevel: 'importer',
    },
  });

  const exportMutation = useExportBundle({
    onSuccess: (data) => {
      if (data.streamUrl) {
        setStreamUrl(data.streamUrl);
      }
      setExportedBundle(data.bundle);
    },
  });

  const selectedArtifacts = watch('artifactIds');
  const generateShareLink = watch('generateShareLink');

  const [initialSteps] = useState<ProgressStep[]>([
    { step: 'Collecting artifacts', status: 'pending' },
    { step: 'Resolving dependencies', status: 'pending' },
    { step: 'Compressing bundle', status: 'pending' },
    { step: 'Generating share link', status: 'pending' },
  ]);

  const handleNext = () => {
    if (step === 1 && selectedArtifacts.length === 0) {
      return;
    }
    setStep(step + 1);
  };

  const handleBack = () => {
    setStep(step - 1);
  };

  const toggleArtifact = (artifactId: string) => {
    const current = selectedArtifacts || [];
    if (current.includes(artifactId)) {
      setValue(
        'artifactIds',
        current.filter((id) => id !== artifactId)
      );
    } else {
      setValue('artifactIds', [...current, artifactId]);
    }
  };

  const onSubmit = async (data: ExportFormData) => {
    setIsExporting(true);

    const metadata: BundleMetadata = {
      name: data.name,
      description: data.description || undefined,
      tags: data.tags ? data.tags.split(',').map((t) => t.trim()) : undefined,
      license: data.license || undefined,
      author: data.author || undefined,
      version: data.version || undefined,
      createdAt: new Date().toISOString(),
    };

    const options: ExportOptions = {
      includeDependencies: data.includeDependencies,
      compressionLevel: data.compressionLevel,
      format: data.format,
      generateShareLink: data.generateShareLink,
      linkExpiration: data.linkExpiration,
      permissionLevel: data.permissionLevel,
    };

    const request: ExportRequest = {
      artifactIds: data.artifactIds,
      metadata,
      options,
    };

    try {
      await exportMutation.mutateAsync(request);
    } catch (error) {
      console.error('Export failed:', error);
      setIsExporting(false);
    }
  };

  const handleComplete = (success: boolean) => {
    setIsExporting(false);
    if (success) {
      setStep(4); // Go to success step
    }
  };

  const handleClose = () => {
    if (!isExporting) {
      onClose();
      // Reset state
      setStep(1);
      setStreamUrl(null);
      setExportedBundle(null);
      setIsExporting(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && handleClose()}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-[600px]">
        <DialogHeader>
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-primary/10 p-2">
              <Package className="h-5 w-5 text-primary" />
            </div>
            <div>
              <DialogTitle>Export Bundle</DialogTitle>
              <DialogDescription>
                {step === 1 && 'Select artifacts to include'}
                {step === 2 && 'Configure bundle metadata'}
                {step === 3 && 'Set export options'}
                {step === 4 && 'Export complete'}
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 py-4">
          {/* Step 1: Artifact Selection */}
          {step === 1 && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <Label>Select Artifacts</Label>
                <span className="text-sm text-muted-foreground">
                  {selectedArtifacts.length} selected
                </span>
              </div>
              <div className="max-h-96 overflow-y-auto rounded-lg border">
                {artifacts.length === 0 ? (
                  <div className="p-8 text-center text-muted-foreground">
                    No artifacts available
                  </div>
                ) : (
                  <div className="divide-y">
                    {artifacts.map((artifact: Artifact) => (
                      <div
                        key={artifact.id}
                        className="cursor-pointer p-3 hover:bg-muted/50"
                        onClick={() => toggleArtifact(artifact.id)}
                      >
                        <div className="flex items-start gap-3">
                          <Checkbox
                            checked={selectedArtifacts.includes(artifact.id)}
                            onCheckedChange={() => toggleArtifact(artifact.id)}
                            onClick={(e) => e.stopPropagation()}
                          />
                          <div className="min-w-0 flex-1">
                            <p className="text-sm font-medium">{artifact.name}</p>
                            {artifact.description && (
                              <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">
                                {artifact.description}
                              </p>
                            )}
                            <div className="mt-2 flex items-center gap-2">
                              <span className="rounded bg-muted px-2 py-0.5 text-xs capitalize">
                                {artifact.type}
                              </span>
                              {artifact.version && (
                                <code className="rounded bg-muted px-2 py-0.5 text-xs">
                                  {artifact.version}
                                </code>
                              )}
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Step 2: Metadata */}
          {step === 2 && (
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="name">Bundle Name *</Label>
                <Input
                  id="name"
                  placeholder="My Artifact Bundle"
                  {...register('name', { required: true })}
                />
                {errors.name && <p className="text-sm text-destructive">Name is required</p>}
              </div>

              <div className="space-y-2">
                <Label htmlFor="description">Description</Label>
                <Textarea
                  id="description"
                  placeholder="Describe what this bundle contains..."
                  rows={3}
                  {...register('description')}
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="version">Version</Label>
                  <Input id="version" placeholder="1.0.0" {...register('version')} />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="license">License</Label>
                  <Input id="license" placeholder="MIT" {...register('license')} />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="author">Author</Label>
                <Input
                  id="author"
                  placeholder="Your name or organization"
                  {...register('author')}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="tags">Tags</Label>
                <Input
                  id="tags"
                  placeholder="web, frontend, development (comma-separated)"
                  {...register('tags')}
                />
                <p className="text-xs text-muted-foreground">Separate multiple tags with commas</p>
              </div>
            </div>
          )}

          {/* Step 3: Options & Share Settings */}
          {step === 3 && !isExporting && (
            <div className="space-y-4">
              <div className="space-y-3">
                <h4 className="flex items-center gap-2 text-sm font-medium">
                  <Settings className="h-4 w-4" />
                  Export Options
                </h4>

                <div className="flex items-center space-x-2">
                  <Checkbox id="includeDependencies" {...register('includeDependencies')} />
                  <Label htmlFor="includeDependencies" className="cursor-pointer">
                    Include dependencies
                  </Label>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="format">Format</Label>
                    <select
                      id="format"
                      className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm"
                      {...register('format')}
                    >
                      <option value="zip">ZIP</option>
                      <option value="tar.gz">TAR.GZ</option>
                    </select>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="compressionLevel">Compression</Label>
                    <select
                      id="compressionLevel"
                      className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm"
                      {...register('compressionLevel')}
                    >
                      <option value="none">None</option>
                      <option value="fast">Fast</option>
                      <option value="balanced">Balanced</option>
                      <option value="best">Best</option>
                    </select>
                  </div>
                </div>
              </div>

              <div className="space-y-3 border-t pt-4">
                <h4 className="flex items-center gap-2 text-sm font-medium">
                  <Share2 className="h-4 w-4" />
                  Share Settings
                </h4>

                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="generateShareLink"
                    checked={generateShareLink}
                    onCheckedChange={(checked) => setValue('generateShareLink', checked as boolean)}
                  />
                  <Label htmlFor="generateShareLink" className="cursor-pointer">
                    Generate shareable link
                  </Label>
                </div>

                {generateShareLink && (
                  <>
                    <div className="space-y-2 pl-6">
                      <Label htmlFor="permissionLevel">Permission Level</Label>
                      <select
                        id="permissionLevel"
                        className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm"
                        {...register('permissionLevel')}
                      >
                        <option value="viewer">Viewer (view only)</option>
                        <option value="importer">Importer (can import)</option>
                        <option value="publisher">Publisher (can modify)</option>
                        <option value="admin">Admin (full access)</option>
                      </select>
                    </div>

                    <div className="space-y-2 pl-6">
                      <Label htmlFor="linkExpiration">Link Expiration</Label>
                      <select
                        id="linkExpiration"
                        className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm"
                        {...register('linkExpiration', { valueAsNumber: true })}
                      >
                        <option value="0">Never</option>
                        <option value="24">24 hours</option>
                        <option value="168">7 days</option>
                        <option value="720">30 days</option>
                      </select>
                    </div>
                  </>
                )}
              </div>
            </div>
          )}

          {/* Step 3: Progress Indicator */}
          {step === 3 && isExporting && (
            <ProgressIndicator
              streamUrl={streamUrl}
              enabled={isExporting}
              initialSteps={initialSteps}
              onComplete={handleComplete}
              onError={(error) => {
                console.error('Export error:', error);
                setIsExporting(false);
              }}
            />
          )}

          {/* Step 4: Success */}
          {step === 4 && exportedBundle && (
            <div className="space-y-4">
              <div className="flex flex-col items-center justify-center py-6 text-center">
                <div className="mb-4 rounded-full bg-green-100 p-3 dark:bg-green-900/20">
                  <CheckCircle className="h-8 w-8 text-green-600" />
                </div>
                <h3 className="mb-2 text-lg font-semibold">Export Complete!</h3>
                <p className="text-sm text-muted-foreground">
                  Your bundle has been created successfully
                </p>
              </div>

              <div className="space-y-2 rounded-lg border p-4">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Bundle Name</span>
                  <span className="font-medium">{exportedBundle.metadata.name}</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Artifacts</span>
                  <span className="font-medium">{exportedBundle.artifacts.length}</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Size</span>
                  <span className="font-medium">
                    {(exportedBundle.size / 1024 / 1024).toFixed(2)} MB
                  </span>
                </div>
              </div>

              {exportedBundle.shareLink && (
                <ShareLink shareLink={exportedBundle.shareLink} showAnalytics={false} />
              )}

              <Button className="w-full" variant="outline">
                <Download className="mr-2 h-4 w-4" />
                Download Bundle
              </Button>
            </div>
          )}
        </form>

        <DialogFooter>
          {step > 1 && step < 4 && !isExporting && (
            <Button variant="outline" onClick={handleBack}>
              <ChevronLeft className="mr-2 h-4 w-4" />
              Back
            </Button>
          )}
          {step < 3 && (
            <Button onClick={handleNext} disabled={step === 1 && selectedArtifacts.length === 0}>
              Next
              <ChevronRight className="ml-2 h-4 w-4" />
            </Button>
          )}
          {step === 3 && !isExporting && (
            <Button type="submit" onClick={handleSubmit(onSubmit)}>
              <Package className="mr-2 h-4 w-4" />
              Export Bundle
            </Button>
          )}
          {step === 4 && <Button onClick={handleClose}>Done</Button>}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
