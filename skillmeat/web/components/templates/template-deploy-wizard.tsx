'use client';

import { useState } from 'react';
import {
  Check,
  ChevronLeft,
  ChevronRight,
  Loader2,
  Folder,
  FileText,
  AlertTriangle,
  CheckCircle,
  XCircle,
  FolderTree,
} from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Checkbox } from '@/components/ui/checkbox';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertTitle, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

interface TemplateEntity {
  artifact_id: string;
  name: string;
  type: string;
  deploy_order: number;
  required: boolean;
  path_pattern: string | null;
}

interface DeploymentResult {
  success: boolean;
  message?: string;
  deployed_files?: Array<{
    path: string;
    status: 'deployed' | 'skipped' | 'error';
    message?: string;
  }>;
  errors?: string[];
}

export interface TemplateDeployWizardProps {
  template: {
    id: string;
    name: string;
    description: string | null;
    entities: TemplateEntity[];
  };
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: (result: DeploymentResult) => void;
}

interface FormData {
  projectName: string;
  projectPath: string;
  variables: {
    PROJECT_NAME: string;
    PROJECT_DESCRIPTION: string;
    AUTHOR: string;
    DATE: string;
    ARCHITECTURE_DESCRIPTION: string;
  };
  selectedEntityIds: string[];
  overwrite: boolean;
}

const STEPS = [
  { id: 1, title: 'Project Config', description: 'Configure project details' },
  { id: 2, title: 'Variables', description: 'Set template variables' },
  { id: 3, title: 'Select Entities', description: 'Choose what to deploy' },
  { id: 4, title: 'Confirm', description: 'Review deployment' },
  { id: 5, title: 'Deploy', description: 'Deployment in progress' },
  { id: 6, title: 'Complete', description: 'Deployment result' },
];

export function TemplateDeployWizard({
  template,
  open,
  onOpenChange,
  onSuccess,
}: TemplateDeployWizardProps) {
  const [step, setStep] = useState(1);
  const [formData, setFormData] = useState<FormData>({
    projectName: '',
    projectPath: '',
    variables: {
      PROJECT_NAME: '',
      PROJECT_DESCRIPTION: '',
      AUTHOR: '',
      DATE: new Date().toISOString().split('T')[0] ?? '',
      ARCHITECTURE_DESCRIPTION: '',
    },
    selectedEntityIds: template.entities.filter((e) => e.required).map((e) => e.artifact_id),
    overwrite: false,
  });
  const [isDeploying, setIsDeploying] = useState(false);
  const [deployResult, setDeployResult] = useState<DeploymentResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});

  const updateFormData = (updates: Partial<FormData>) => {
    setFormData((prev) => ({ ...prev, ...updates }));
  };

  const updateVariables = (updates: Partial<FormData['variables']>) => {
    setFormData((prev) => ({
      ...prev,
      variables: { ...prev.variables, ...updates },
    }));
  };

  const validateStep = (stepNumber: number): boolean => {
    const errors: Record<string, string> = {};

    if (stepNumber === 1) {
      if (!formData.projectName.trim()) {
        errors.projectName = 'Project name is required';
      }
      if (!formData.projectPath.trim()) {
        errors.projectPath = 'Project path is required';
      } else if (formData.projectPath.includes('..')) {
        errors.projectPath = 'Path cannot contain ".."';
      } else if (!formData.projectPath.startsWith('/')) {
        errors.projectPath = 'Path must be absolute (start with /)';
      }
    } else if (stepNumber === 2) {
      if (!formData.variables.PROJECT_NAME.trim()) {
        errors.PROJECT_NAME = 'PROJECT_NAME is required';
      }
    } else if (stepNumber === 3) {
      const requiredEntities = template.entities.filter((e) => e.required);
      const missingRequired = requiredEntities.filter(
        (e) => !formData.selectedEntityIds.includes(e.artifact_id)
      );
      if (missingRequired.length > 0) {
        errors.selectedEntityIds = 'All required entities must be selected';
      }
    }

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleNext = () => {
    if (!validateStep(step)) {
      return;
    }

    if (step === 1) {
      // Auto-fill PROJECT_NAME from projectName
      updateVariables({ PROJECT_NAME: formData.projectName });
    }

    if (step < 4) {
      setStep(step + 1);
    } else if (step === 4) {
      // Start deployment
      handleDeploy();
    }
  };

  const handleBack = () => {
    if (step > 1 && step < 5) {
      setStep(step - 1);
      setValidationErrors({});
    }
  };

  const handleDeploy = async () => {
    setStep(5);
    setIsDeploying(true);
    setError(null);

    try {
      // Build API URL
      const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';
      const API_VERSION = process.env.NEXT_PUBLIC_API_VERSION || 'v1';
      const url = `${API_BASE}/api/${API_VERSION}/project-templates/${template.id}/deploy`;

      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_path: formData.projectPath,
          variables: formData.variables,
          selected_entity_ids: formData.selectedEntityIds,
          overwrite: formData.overwrite,
        }),
      });

      if (!response.ok) {
        const errorBody = await response.json().catch(() => ({}));
        throw new Error(errorBody.detail || `Deployment failed: ${response.statusText}`);
      }

      const result: DeploymentResult = await response.json();
      setDeployResult(result);
      setStep(6);
      onSuccess?.(result);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Deployment failed';
      setError(errorMessage);
      setDeployResult({
        success: false,
        message: errorMessage,
        errors: [errorMessage],
      });
      setStep(6);
    } finally {
      setIsDeploying(false);
    }
  };

  const handleClose = () => {
    if (!isDeploying) {
      onOpenChange(false);
      // Reset state
      setTimeout(() => {
        setStep(1);
        setFormData({
          projectName: '',
          projectPath: '',
          variables: {
            PROJECT_NAME: '',
            PROJECT_DESCRIPTION: '',
            AUTHOR: '',
            DATE: new Date().toISOString().split('T')[0] ?? '',
            ARCHITECTURE_DESCRIPTION: '',
          },
          selectedEntityIds: template.entities.filter((e) => e.required).map((e) => e.artifact_id),
          overwrite: false,
        });
        setDeployResult(null);
        setError(null);
        setValidationErrors({});
      }, 200);
    }
  };

  const toggleEntitySelection = (artifactId: string) => {
    setFormData((prev) => ({
      ...prev,
      selectedEntityIds: prev.selectedEntityIds.includes(artifactId)
        ? prev.selectedEntityIds.filter((id) => id !== artifactId)
        : [...prev.selectedEntityIds, artifactId],
    }));
  };

  const selectAll = () => {
    updateFormData({
      selectedEntityIds: template.entities.map((e) => e.artifact_id),
    });
  };

  const selectRequiredOnly = () => {
    updateFormData({
      selectedEntityIds: template.entities.filter((e) => e.required).map((e) => e.artifact_id),
    });
  };

  const progress = (step / STEPS.length) * 100;

  return (
    <Dialog open={open} onOpenChange={(open) => !open && handleClose()}>
      <DialogContent className="flex max-h-[90vh] max-w-3xl flex-col overflow-hidden p-0">
        {/* Header - Fixed */}
        <div className="border-b px-6 pb-4 pt-6">
          <DialogHeader>
            <div className="flex items-center gap-3">
              <div className="rounded-lg bg-primary/10 p-2">
                <FolderTree className="h-5 w-5 text-primary" />
              </div>
              <div>
                <DialogTitle>Deploy Template: {template.name}</DialogTitle>
                <DialogDescription>
                  Step {step} of {STEPS.length}: {STEPS[step - 1]?.title ?? ''}
                </DialogDescription>
              </div>
            </div>
          </DialogHeader>

          {/* Progress Bar */}
          <div className="mt-4 space-y-2">
            <Progress value={progress} className="h-2" />
            <div className="flex items-center justify-between">
              {STEPS.map((s, index) => {
                const isActive = s.id === step;
                const isCompleted = s.id < step;

                return (
                  <div key={s.id} className="flex items-center">
                    <div className="flex flex-col items-center">
                      <div
                        className={cn(
                          'flex h-6 w-6 items-center justify-center rounded-full border-2 text-xs',
                          isActive &&
                            'border-primary bg-primary font-medium text-primary-foreground',
                          isCompleted && 'border-green-500 bg-green-500 text-white',
                          !isActive && !isCompleted && 'border-muted-foreground bg-background'
                        )}
                      >
                        {isCompleted ? <Check className="h-3 w-3" /> : <span>{s.id}</span>}
                      </div>
                      <p
                        className={cn(
                          'mt-1 hidden max-w-[70px] text-center text-xs sm:block',
                          isActive ? 'font-medium' : 'text-muted-foreground'
                        )}
                      >
                        {s.title}
                      </p>
                    </div>
                    {index < STEPS.length - 1 && (
                      <div
                        className={cn(
                          'mx-1 h-0.5 w-8 sm:w-12',
                          isCompleted ? 'bg-green-500' : 'bg-muted'
                        )}
                      />
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Content - Scrollable */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {/* Step 1: Project Configuration */}
          {step === 1 && (
            <div className="space-y-4">
              <div>
                <h3 className="mb-1 text-lg font-semibold">Project Configuration</h3>
                <p className="text-sm text-muted-foreground">
                  Configure where to deploy this template
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="projectName">
                  Project Name <span className="text-destructive">*</span>
                </Label>
                <Input
                  id="projectName"
                  placeholder="my-awesome-project"
                  value={formData.projectName}
                  onChange={(e) => {
                    updateFormData({ projectName: e.target.value });
                    setValidationErrors((prev) => ({ ...prev, projectName: '' }));
                  }}
                  className={validationErrors.projectName ? 'border-destructive' : ''}
                />
                {validationErrors.projectName && (
                  <p className="text-sm text-destructive">{validationErrors.projectName}</p>
                )}
                <p className="text-xs text-muted-foreground">
                  Will be used for PROJECT_NAME variable
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="projectPath">
                  Project Path <span className="text-destructive">*</span>
                </Label>
                <Input
                  id="projectPath"
                  placeholder="/Users/dev/my-project"
                  value={formData.projectPath}
                  onChange={(e) => {
                    updateFormData({ projectPath: e.target.value });
                    setValidationErrors((prev) => ({ ...prev, projectPath: '' }));
                  }}
                  className={validationErrors.projectPath ? 'border-destructive' : ''}
                />
                {validationErrors.projectPath && (
                  <p className="text-sm text-destructive">{validationErrors.projectPath}</p>
                )}
                <p className="text-xs text-muted-foreground">
                  Absolute path where .claude/ directory will be created
                </p>
              </div>

              <Alert>
                <Folder className="h-4 w-4" />
                <AlertTitle>Path Requirements</AlertTitle>
                <AlertDescription>
                  Path must be absolute (start with /), cannot contain "..", and should point to an
                  existing or new project directory.
                </AlertDescription>
              </Alert>
            </div>
          )}

          {/* Step 2: Template Variables */}
          {step === 2 && (
            <div className="space-y-4">
              <div>
                <h3 className="mb-1 text-lg font-semibold">Template Variables</h3>
                <p className="text-sm text-muted-foreground">
                  These variables will be substituted in template files
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="PROJECT_NAME">
                  PROJECT_NAME <span className="text-destructive">*</span>
                </Label>
                <Input
                  id="PROJECT_NAME"
                  value={formData.variables.PROJECT_NAME}
                  onChange={(e) => {
                    updateVariables({ PROJECT_NAME: e.target.value });
                    setValidationErrors((prev) => ({ ...prev, PROJECT_NAME: '' }));
                  }}
                  className={validationErrors.PROJECT_NAME ? 'border-destructive' : ''}
                />
                {validationErrors.PROJECT_NAME && (
                  <p className="text-sm text-destructive">{validationErrors.PROJECT_NAME}</p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="PROJECT_DESCRIPTION">PROJECT_DESCRIPTION (Optional)</Label>
                <Textarea
                  id="PROJECT_DESCRIPTION"
                  placeholder="A brief description of your project..."
                  value={formData.variables.PROJECT_DESCRIPTION}
                  onChange={(e) => updateVariables({ PROJECT_DESCRIPTION: e.target.value })}
                  rows={3}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="AUTHOR">AUTHOR (Optional)</Label>
                <Input
                  id="AUTHOR"
                  placeholder="Your Name"
                  value={formData.variables.AUTHOR}
                  onChange={(e) => updateVariables({ AUTHOR: e.target.value })}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="DATE">DATE</Label>
                <Input
                  id="DATE"
                  type="date"
                  value={formData.variables.DATE}
                  onChange={(e) => updateVariables({ DATE: e.target.value })}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="ARCHITECTURE_DESCRIPTION">
                  ARCHITECTURE_DESCRIPTION (Optional)
                </Label>
                <Textarea
                  id="ARCHITECTURE_DESCRIPTION"
                  placeholder="Describe the project architecture..."
                  value={formData.variables.ARCHITECTURE_DESCRIPTION}
                  onChange={(e) => updateVariables({ ARCHITECTURE_DESCRIPTION: e.target.value })}
                  rows={3}
                />
              </div>

              {formData.variables.PROJECT_NAME && (
                <div className="rounded-lg border bg-muted/50 p-3">
                  <p className="mb-2 text-xs font-medium">Variable Preview</p>
                  <p className="font-mono text-xs text-muted-foreground">
                    Project: {formData.variables.PROJECT_NAME || '{{PROJECT_NAME}}'} by{' '}
                    {formData.variables.AUTHOR || '{{AUTHOR}}'} on{' '}
                    {formData.variables.DATE || '{{DATE}}'}
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Step 3: Entity Selection */}
          {step === 3 && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="mb-1 text-lg font-semibold">Select Entities</h3>
                  <p className="text-sm text-muted-foreground">
                    Choose which entities to deploy ({formData.selectedEntityIds.length}/
                    {template.entities.length} selected)
                  </p>
                </div>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={selectRequiredOnly}>
                    Required Only
                  </Button>
                  <Button variant="outline" size="sm" onClick={selectAll}>
                    Select All
                  </Button>
                </div>
              </div>

              {validationErrors.selectedEntityIds && (
                <Alert variant="destructive">
                  <AlertTriangle className="h-4 w-4" />
                  <AlertDescription>{validationErrors.selectedEntityIds}</AlertDescription>
                </Alert>
              )}

              <div className="space-y-2">
                {template.entities
                  .sort((a, b) => a.deploy_order - b.deploy_order)
                  .map((entity) => {
                    const isSelected = formData.selectedEntityIds.includes(entity.artifact_id);
                    const isRequired = entity.required;

                    return (
                      <div
                        key={entity.artifact_id}
                        className={cn(
                          'flex items-start gap-3 rounded-lg border p-3',
                          isSelected && 'bg-muted/50'
                        )}
                      >
                        <Checkbox
                          checked={isSelected}
                          onCheckedChange={() => toggleEntitySelection(entity.artifact_id)}
                          disabled={isRequired}
                          className="mt-1"
                        />
                        <div className="flex-1 space-y-1">
                          <div className="flex items-center gap-2">
                            <FileText className="h-4 w-4 text-muted-foreground" />
                            <h4 className="font-medium">{entity.name}</h4>
                            <Badge variant="outline" className="text-xs capitalize">
                              {entity.type.replace('_', ' ')}
                            </Badge>
                            {isRequired && (
                              <Badge variant="default" className="text-xs">
                                Required
                              </Badge>
                            )}
                          </div>
                          {entity.path_pattern && (
                            <p className="font-mono text-xs text-muted-foreground">
                              {entity.path_pattern}
                            </p>
                          )}
                        </div>
                      </div>
                    );
                  })}
              </div>
            </div>
          )}

          {/* Step 4: Confirmation */}
          {step === 4 && (
            <div className="space-y-4">
              <div>
                <h3 className="mb-1 text-lg font-semibold">Review & Confirm</h3>
                <p className="text-sm text-muted-foreground">
                  Please review your deployment configuration
                </p>
              </div>

              <div className="space-y-3 rounded-lg border p-4">
                <div className="flex justify-between border-b pb-2">
                  <span className="text-sm font-medium">Template:</span>
                  <span className="text-sm">{template.name}</span>
                </div>
                <div className="flex justify-between border-b pb-2">
                  <span className="text-sm font-medium">Project Name:</span>
                  <span className="text-sm">{formData.projectName}</span>
                </div>
                <div className="flex justify-between border-b pb-2">
                  <span className="text-sm font-medium">Project Path:</span>
                  <span className="truncate font-mono text-sm">{formData.projectPath}</span>
                </div>
                <div className="flex justify-between border-b pb-2">
                  <span className="text-sm font-medium">Selected Entities:</span>
                  <span className="text-sm">
                    {formData.selectedEntityIds.length} / {template.entities.length}
                  </span>
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <Checkbox
                    id="overwrite"
                    checked={formData.overwrite}
                    onCheckedChange={(checked) => updateFormData({ overwrite: checked === true })}
                  />
                  <Label htmlFor="overwrite" className="cursor-pointer">
                    Overwrite existing files
                  </Label>
                </div>
              </div>

              <Alert className="border-yellow-500/50 bg-yellow-500/10">
                <AlertTriangle className="h-4 w-4 text-yellow-600" />
                <AlertTitle className="text-yellow-900 dark:text-yellow-100">Warning</AlertTitle>
                <AlertDescription className="text-yellow-800 dark:text-yellow-200">
                  {formData.overwrite
                    ? 'Existing files will be overwritten. Make sure to back up any important files.'
                    : 'Deployment will fail if files already exist. Enable "Overwrite existing files" to replace them.'}
                </AlertDescription>
              </Alert>
            </div>
          )}

          {/* Step 5: Progress */}
          {step === 5 && (
            <div className="space-y-4">
              <div>
                <h3 className="mb-1 text-lg font-semibold">Deploying Template</h3>
                <p className="text-sm text-muted-foreground">
                  Please wait while we deploy your template
                </p>
              </div>

              <div className="flex flex-col items-center justify-center py-12">
                <Loader2 className="h-12 w-12 animate-spin text-primary" />
                <p className="mt-4 text-sm text-muted-foreground">Deployment in progress...</p>
              </div>

              <Progress value={50} className="h-2" />

              <div className="space-y-2">
                {formData.selectedEntityIds.map((entityId) => {
                  const entity = template.entities.find((e) => e.artifact_id === entityId);
                  if (!entity) return null;

                  return (
                    <div key={entityId} className="flex items-center gap-3 rounded-lg border p-3">
                      <Loader2 className="h-4 w-4 animate-spin text-primary" />
                      <div className="flex-1">
                        <p className="text-sm font-medium">{entity.name}</p>
                        <p className="text-xs text-muted-foreground">Deploying...</p>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Step 6: Success/Error */}
          {step === 6 && (
            <div className="space-y-4">
              {deployResult?.success ? (
                <>
                  <div className="flex flex-col items-center justify-center py-8">
                    <div className="rounded-full bg-green-500/10 p-4">
                      <CheckCircle className="h-12 w-12 text-green-600" />
                    </div>
                    <h3 className="mt-4 text-lg font-semibold">Deployment Successful!</h3>
                    <p className="text-sm text-muted-foreground">
                      Template deployed successfully to {formData.projectPath}
                    </p>
                  </div>

                  {deployResult.deployed_files && deployResult.deployed_files.length > 0 && (
                    <div className="space-y-2">
                      <h4 className="text-sm font-medium">Deployed Files</h4>
                      <div className="max-h-60 space-y-1 overflow-y-auto rounded-lg border p-3">
                        {deployResult.deployed_files.map((file, index) => (
                          <div key={index} className="flex items-center gap-2 text-sm">
                            {file.status === 'deployed' && (
                              <CheckCircle className="h-3 w-3 text-green-600" />
                            )}
                            {file.status === 'skipped' && (
                              <AlertTriangle className="h-3 w-3 text-yellow-600" />
                            )}
                            {file.status === 'error' && (
                              <XCircle className="h-3 w-3 text-destructive" />
                            )}
                            <span className="font-mono text-xs">{file.path}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <>
                  <div className="flex flex-col items-center justify-center py-8">
                    <div className="rounded-full bg-destructive/10 p-4">
                      <XCircle className="h-12 w-12 text-destructive" />
                    </div>
                    <h3 className="mt-4 text-lg font-semibold">Deployment Failed</h3>
                    <p className="text-sm text-muted-foreground">
                      {deployResult?.message || error || 'An error occurred during deployment'}
                    </p>
                  </div>

                  {deployResult?.errors && deployResult.errors.length > 0 && (
                    <Alert variant="destructive">
                      <AlertTriangle className="h-4 w-4" />
                      <AlertTitle>Errors</AlertTitle>
                      <AlertDescription>
                        <ul className="list-inside list-disc space-y-1">
                          {deployResult.errors.map((err, index) => (
                            <li key={index} className="text-sm">
                              {err}
                            </li>
                          ))}
                        </ul>
                      </AlertDescription>
                    </Alert>
                  )}
                </>
              )}
            </div>
          )}
        </div>

        {/* Footer - Fixed */}
        <div className="border-t bg-muted/30 px-6 py-4">
          <div className="flex items-center justify-between">
            {step < 5 ? (
              <>
                <Button variant="outline" onClick={handleBack} disabled={step === 1}>
                  <ChevronLeft className="mr-2 h-4 w-4" />
                  Back
                </Button>
                <Button onClick={handleNext} disabled={isDeploying}>
                  {step === 4 ? (
                    <>
                      Deploy
                      <FolderTree className="ml-2 h-4 w-4" />
                    </>
                  ) : (
                    <>
                      Next
                      <ChevronRight className="ml-2 h-4 w-4" />
                    </>
                  )}
                </Button>
              </>
            ) : step === 5 ? (
              <div className="w-full text-center">
                <Button variant="outline" disabled>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Deploying...
                </Button>
              </div>
            ) : (
              <div className="flex w-full items-center justify-between">
                {!deployResult?.success && (
                  <Button variant="outline" onClick={() => setStep(4)}>
                    Try Again
                  </Button>
                )}
                <Button onClick={handleClose} className="ml-auto">
                  Close
                </Button>
              </div>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
