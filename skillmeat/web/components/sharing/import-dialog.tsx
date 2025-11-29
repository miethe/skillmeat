'use client';

/**
 * Import Dialog Component
 *
 * Multi-step wizard for importing artifact bundles
 */

import { useState, useCallback } from 'react';
import { useForm } from 'react-hook-form';
import { useDropzone } from 'react-dropzone';
import {
  Upload,
  ChevronRight,
  ChevronLeft,
  FileArchive,
  Link2,
  Cloud,
  CheckCircle,
  AlertTriangle,
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ProgressIndicator, ProgressStep } from '../collection/progress-indicator';
import { BundlePreview } from './bundle-preview';
import { usePreviewBundle, useImportBundle } from '@/hooks/useImportBundle';
import type { ImportRequest, BundleSource, ImportOptions, ConflictStrategy } from '@/types/bundle';

export interface ImportDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

type ImportFormData = {
  sourceType: 'file' | 'url' | 'vault';
  url?: string;
  vaultProvider?: string;
  vaultPath?: string;
  conflictStrategy: ConflictStrategy;
  skipValidation: boolean;
  dryRun: boolean;
};

export function ImportDialog({ isOpen, onClose, onSuccess }: ImportDialogProps) {
  const [step, setStep] = useState(1);
  const [isImporting, setIsImporting] = useState(false);
  const [streamUrl, setStreamUrl] = useState<string | null>(null);
  const [importResult, setImportResult] = useState<any>(null);
  const [bundleSource, setBundleSource] = useState<BundleSource | null>(null);
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors },
  } = useForm<ImportFormData>({
    defaultValues: {
      sourceType: 'file',
      conflictStrategy: 'merge',
      skipValidation: false,
      dryRun: false,
    },
  });

  const sourceType = watch('sourceType');
  const conflictStrategy = watch('conflictStrategy');

  const { data: preview, isLoading: isLoadingPreview } = usePreviewBundle(bundleSource, step === 2);

  const importMutation = useImportBundle({
    onSuccess: (data) => {
      if (data.streamUrl) {
        setStreamUrl(data.streamUrl);
      }
      setImportResult(data.result);
    },
  });

  const [initialSteps] = useState<ProgressStep[]>([
    { step: 'Uploading bundle', status: 'pending' },
    { step: 'Validating contents', status: 'pending' },
    { step: 'Resolving conflicts', status: 'pending' },
    { step: 'Installing artifacts', status: 'pending' },
  ]);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      const file = acceptedFiles[0];
      if (file) {
        setUploadedFile(file);
        setBundleSource({ type: 'file', file });
      }
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/zip': ['.zip'],
      'application/gzip': ['.tar.gz', '.tgz'],
    },
    maxFiles: 1,
  });

  const handleNext = () => {
    if (step === 1) {
      // Set bundle source based on type
      if (sourceType === 'file' && !uploadedFile) {
        return;
      }
      if (sourceType === 'url') {
        const url = watch('url');
        if (!url) return;
        setBundleSource({ type: 'url', url });
      }
      if (sourceType === 'vault') {
        const vaultProvider = watch('vaultProvider');
        const vaultPath = watch('vaultPath');
        if (!vaultProvider || !vaultPath) return;
        setBundleSource({
          type: 'vault',
          vault: { provider: vaultProvider as any },
          path: vaultPath,
        });
      }
    }
    setStep(step + 1);
  };

  const handleBack = () => {
    setStep(step - 1);
  };

  const onSubmit = async (data: ImportFormData) => {
    if (!bundleSource) return;

    setIsImporting(true);

    const options: ImportOptions = {
      conflictStrategy: data.conflictStrategy,
      skipValidation: data.skipValidation,
      dryRun: data.dryRun,
    };

    const importReq: ImportRequest = {
      source: bundleSource,
      options,
    };

    try {
      await importMutation.mutateAsync(importReq);
    } catch (error) {
      console.error('Import failed:', error);
      setIsImporting(false);
    }
  };

  const handleComplete = (success: boolean) => {
    setIsImporting(false);
    if (success) {
      setStep(4); // Go to success step
    }
  };

  const handleClose = () => {
    if (!isImporting) {
      onClose();
      // Reset state
      setStep(1);
      setStreamUrl(null);
      setImportResult(null);
      setBundleSource(null);
      setUploadedFile(null);
      setIsImporting(false);
    }
  };

  const handleDone = () => {
    onSuccess?.();
    handleClose();
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && handleClose()}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-[700px]">
        <DialogHeader>
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-primary/10 p-2">
              <Upload className="h-5 w-5 text-primary" />
            </div>
            <div>
              <DialogTitle>Import Bundle</DialogTitle>
              <DialogDescription>
                {step === 1 && 'Select bundle source'}
                {step === 2 && 'Review and configure import'}
                {step === 3 && 'Importing artifacts'}
                {step === 4 && 'Import complete'}
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 py-4">
          {/* Step 1: Source Selection */}
          {step === 1 && (
            <div className="space-y-4">
              <Tabs
                value={sourceType}
                onValueChange={(value) => {
                  setValue('sourceType', value as any);
                  setUploadedFile(null);
                  setBundleSource(null);
                }}
              >
                <TabsList className="grid w-full grid-cols-3">
                  <TabsTrigger value="file">
                    <FileArchive className="mr-2 h-4 w-4" />
                    File
                  </TabsTrigger>
                  <TabsTrigger value="url">
                    <Link2 className="mr-2 h-4 w-4" />
                    URL
                  </TabsTrigger>
                  <TabsTrigger value="vault">
                    <Cloud className="mr-2 h-4 w-4" />
                    Vault
                  </TabsTrigger>
                </TabsList>

                <TabsContent value="file" className="space-y-4">
                  <div
                    {...getRootProps()}
                    className={`cursor-pointer rounded-lg border-2 border-dashed p-8 text-center transition-colors ${
                      isDragActive
                        ? 'border-primary bg-primary/5'
                        : 'border-muted-foreground/25 hover:border-primary/50'
                    }`}
                  >
                    <input {...getInputProps()} />
                    <Upload className="mx-auto mb-4 h-12 w-12 text-muted-foreground" />
                    {uploadedFile ? (
                      <div>
                        <p className="font-medium">{uploadedFile.name}</p>
                        <p className="mt-1 text-sm text-muted-foreground">
                          {(uploadedFile.size / 1024 / 1024).toFixed(2)} MB
                        </p>
                        <Button
                          variant="outline"
                          size="sm"
                          className="mt-4"
                          onClick={(e) => {
                            e.stopPropagation();
                            setUploadedFile(null);
                            setBundleSource(null);
                          }}
                        >
                          Choose Different File
                        </Button>
                      </div>
                    ) : (
                      <div>
                        <p className="mb-2 font-medium">
                          {isDragActive ? 'Drop bundle file here' : 'Drag & drop bundle file here'}
                        </p>
                        <p className="text-sm text-muted-foreground">or click to browse</p>
                        <p className="mt-2 text-xs text-muted-foreground">
                          Supports .zip, .tar.gz files
                        </p>
                      </div>
                    )}
                  </div>
                </TabsContent>

                <TabsContent value="url" className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="url">Bundle URL</Label>
                    <Input
                      id="url"
                      placeholder="https://example.com/bundles/my-bundle.zip"
                      {...register('url', {
                        required: sourceType === 'url',
                      })}
                    />
                    {errors.url && <p className="text-sm text-destructive">URL is required</p>}
                    <p className="text-xs text-muted-foreground">
                      Direct link to a .zip or .tar.gz bundle file
                    </p>
                  </div>
                </TabsContent>

                <TabsContent value="vault" className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="vaultProvider">Vault Provider</Label>
                    <select
                      id="vaultProvider"
                      className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm"
                      {...register('vaultProvider', {
                        required: sourceType === 'vault',
                      })}
                    >
                      <option value="">Select provider...</option>
                      <option value="github">GitHub</option>
                      <option value="s3">Amazon S3</option>
                      <option value="gdrive">Google Drive</option>
                    </select>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="vaultPath">Path</Label>
                    <Input
                      id="vaultPath"
                      placeholder="bundles/my-bundle.zip"
                      {...register('vaultPath', {
                        required: sourceType === 'vault',
                      })}
                    />
                    <p className="text-xs text-muted-foreground">
                      Path to the bundle file in the vault
                    </p>
                  </div>
                </TabsContent>
              </Tabs>
            </div>
          )}

          {/* Step 2: Preview & Configure */}
          {step === 2 && !isImporting && (
            <div className="space-y-4">
              {isLoadingPreview ? (
                <div className="p-8 text-center text-muted-foreground">
                  Loading bundle preview...
                </div>
              ) : preview ? (
                <>
                  <BundlePreview preview={preview} />

                  <div className="space-y-3 border-t pt-4">
                    <h4 className="text-sm font-medium">Import Options</h4>

                    <div className="space-y-2">
                      <Label htmlFor="conflictStrategy">Conflict Strategy</Label>
                      <select
                        id="conflictStrategy"
                        className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm"
                        {...register('conflictStrategy')}
                      >
                        <option value="merge">Merge - Update existing artifacts</option>
                        <option value="fork">Fork - Create renamed copies</option>
                        <option value="skip">Skip - Keep existing artifacts</option>
                        <option value="overwrite">Overwrite - Replace completely</option>
                      </select>
                      <p className="text-xs text-muted-foreground">
                        {conflictStrategy === 'merge' &&
                          'Existing artifacts will be updated with new versions'}
                        {conflictStrategy === 'fork' &&
                          'Conflicts will create new artifacts with modified names'}
                        {conflictStrategy === 'skip' && 'Existing artifacts will not be modified'}
                        {conflictStrategy === 'overwrite' &&
                          'Existing artifacts will be completely replaced'}
                      </p>
                    </div>

                    {preview.conflicts.length > 0 && (
                      <div className="rounded-lg border border-yellow-500/50 bg-yellow-500/10 p-3">
                        <div className="flex items-start gap-2">
                          <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0 text-yellow-600" />
                          <div className="text-sm">
                            <p className="font-medium text-yellow-900 dark:text-yellow-100">
                              {preview.conflicts.length} conflict
                              {preview.conflicts.length > 1 ? 's' : ''} detected
                            </p>
                            <p className="mt-1 text-yellow-800 dark:text-yellow-200">
                              Strategy "{conflictStrategy}" will be applied to all conflicts
                            </p>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                </>
              ) : (
                <div className="p-8 text-center text-destructive">
                  Failed to load bundle preview
                </div>
              )}
            </div>
          )}

          {/* Step 3: Progress Indicator */}
          {step === 3 && isImporting && (
            <ProgressIndicator
              streamUrl={streamUrl}
              enabled={isImporting}
              initialSteps={initialSteps}
              onComplete={handleComplete}
              onError={(error) => {
                console.error('Import error:', error);
                setIsImporting(false);
              }}
            />
          )}

          {/* Step 4: Success */}
          {step === 4 && importResult && (
            <div className="space-y-4">
              <div className="flex flex-col items-center justify-center py-6 text-center">
                <div
                  className={`mb-4 rounded-full p-3 ${
                    importResult.success
                      ? 'bg-green-100 dark:bg-green-900/20'
                      : 'bg-yellow-100 dark:bg-yellow-900/20'
                  }`}
                >
                  <CheckCircle
                    className={`h-8 w-8 ${
                      importResult.success ? 'text-green-600' : 'text-yellow-600'
                    }`}
                  />
                </div>
                <h3 className="mb-2 text-lg font-semibold">
                  {importResult.success ? 'Import Complete!' : 'Import Completed with Warnings'}
                </h3>
                <p className="text-sm text-muted-foreground">{importResult.summary}</p>
              </div>

              <div className="space-y-2 rounded-lg border p-4">
                {importResult.imported.length > 0 && (
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Imported</span>
                    <span className="font-medium text-green-600">
                      {importResult.imported.length}
                    </span>
                  </div>
                )}
                {importResult.merged.length > 0 && (
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Merged</span>
                    <span className="font-medium text-blue-600">{importResult.merged.length}</span>
                  </div>
                )}
                {importResult.forked.length > 0 && (
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Forked</span>
                    <span className="font-medium text-purple-600">
                      {importResult.forked.length}
                    </span>
                  </div>
                )}
                {importResult.skipped.length > 0 && (
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Skipped</span>
                    <span className="font-medium text-muted-foreground">
                      {importResult.skipped.length}
                    </span>
                  </div>
                )}
              </div>

              {importResult.errors.length > 0 && (
                <div className="space-y-2 rounded-lg border border-destructive/50 p-3">
                  <p className="text-sm font-medium text-destructive">Errors</p>
                  {importResult.errors.map((error: any, index: number) => (
                    <div key={index} className="text-xs text-destructive/80">
                      <strong>{error.artifactName}:</strong> {error.error}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </form>

        <DialogFooter>
          {step > 1 && step < 4 && !isImporting && (
            <Button variant="outline" onClick={handleBack}>
              <ChevronLeft className="mr-2 h-4 w-4" />
              Back
            </Button>
          )}
          {step === 1 && (
            <Button
              onClick={handleNext}
              disabled={
                (sourceType === 'file' && !uploadedFile) ||
                (sourceType === 'url' && !watch('url')) ||
                (sourceType === 'vault' && (!watch('vaultProvider') || !watch('vaultPath')))
              }
            >
              Next
              <ChevronRight className="ml-2 h-4 w-4" />
            </Button>
          )}
          {step === 2 && !isImporting && (
            <Button
              onClick={() => {
                handleSubmit(onSubmit)();
                setIsImporting(true);
                setStep(3);
              }}
              disabled={!preview || isLoadingPreview}
            >
              <Upload className="mr-2 h-4 w-4" />
              Import Bundle
            </Button>
          )}
          {step === 4 && <Button onClick={handleDone}>Done</Button>}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
