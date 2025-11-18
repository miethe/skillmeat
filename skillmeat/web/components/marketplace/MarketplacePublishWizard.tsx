"use client";

import { useState } from "react";
import { Check, ChevronLeft, ChevronRight, Loader2, Upload } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { MarketplaceBrokerSelector } from "./MarketplaceBrokerSelector";
import type { BrokerInfo, PublishFormData, PublishWizardStep } from "@/types/marketplace";

interface MarketplacePublishWizardProps {
  brokers: BrokerInfo[];
  onPublish: (data: PublishFormData) => Promise<void>;
  onCancel: () => void;
}

const STEPS: PublishWizardStep[] = [
  {
    id: 1,
    title: "Select Bundle",
    description: "Choose the bundle to publish",
  },
  {
    id: 2,
    title: "Choose Broker",
    description: "Select marketplace broker",
  },
  {
    id: 3,
    title: "Bundle Metadata",
    description: "Provide additional information",
  },
  {
    id: 4,
    title: "Review & Confirm",
    description: "Review your submission",
  },
];

export function MarketplacePublishWizard({
  brokers,
  onPublish,
  onCancel,
}: MarketplacePublishWizardProps) {
  const [currentStep, setCurrentStep] = useState(1);
  const [formData, setFormData] = useState<PublishFormData>({
    tags: [],
  });
  const [isPublishing, setIsPublishing] = useState(false);
  const [tagInput, setTagInput] = useState("");

  const updateFormData = (updates: Partial<PublishFormData>) => {
    setFormData((prev) => ({ ...prev, ...updates }));
  };

  const handleAddTag = () => {
    const trimmedTag = tagInput.trim().toLowerCase();
    if (!trimmedTag || formData.tags?.includes(trimmedTag)) {
      return;
    }
    updateFormData({ tags: [...(formData.tags || []), trimmedTag] });
    setTagInput("");
  };

  const handleRemoveTag = (tag: string) => {
    updateFormData({
      tags: formData.tags?.filter((t) => t !== tag) || [],
    });
  };

  const handleNext = () => {
    if (currentStep < STEPS.length) {
      setCurrentStep(currentStep + 1);
    }
  };

  const handleBack = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleSubmit = async () => {
    if (!formData.bundle_path || !formData.broker) {
      return;
    }

    setIsPublishing(true);
    try {
      await onPublish(formData);
    } finally {
      setIsPublishing(false);
    }
  };

  const canProceed = () => {
    switch (currentStep) {
      case 1:
        return !!formData.bundle_path;
      case 2:
        return !!formData.broker;
      case 3:
        return true; // Metadata is optional
      case 4:
        return true;
      default:
        return false;
    }
  };

  const progress = (currentStep / STEPS.length) * 100;

  return (
    <div className="space-y-6">
      {/* Progress */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-sm">
          <span className="font-medium">
            Step {currentStep} of {STEPS.length}
          </span>
          <span className="text-muted-foreground">
            {STEPS[currentStep - 1].title}
          </span>
        </div>
        <Progress value={progress} className="h-2" />
      </div>

      {/* Step Indicators */}
      <div className="flex items-center justify-between">
        {STEPS.map((step, index) => {
          const isActive = step.id === currentStep;
          const isCompleted = step.id < currentStep;

          return (
            <div
              key={step.id}
              className={`flex items-center ${
                index < STEPS.length - 1 ? "flex-1" : ""
              }`}
            >
              <div className="flex flex-col items-center">
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center border-2 ${
                    isActive
                      ? "border-primary bg-primary text-primary-foreground"
                      : isCompleted
                      ? "border-green-500 bg-green-500 text-white"
                      : "border-muted-foreground bg-background"
                  }`}
                >
                  {isCompleted ? (
                    <Check className="h-4 w-4" />
                  ) : (
                    <span className="text-sm font-medium">{step.id}</span>
                  )}
                </div>
                <p
                  className={`text-xs mt-1 text-center ${
                    isActive ? "font-medium" : "text-muted-foreground"
                  }`}
                >
                  {step.title}
                </p>
              </div>
              {index < STEPS.length - 1 && (
                <div
                  className={`flex-1 h-0.5 mx-2 ${
                    isCompleted ? "bg-green-500" : "bg-muted"
                  }`}
                />
              )}
            </div>
          );
        })}
      </div>

      {/* Step Content */}
      <Card className="p-6">
        <div className="min-h-[300px]">
          {currentStep === 1 && (
            <div className="space-y-4">
              <div>
                <h3 className="text-lg font-semibold mb-1">
                  Select Bundle to Publish
                </h3>
                <p className="text-sm text-muted-foreground">
                  Enter the path to your signed bundle file
                </p>
              </div>
              <div>
                <label htmlFor="bundle-path" className="block text-sm font-medium mb-2">
                  Bundle Path
                </label>
                <Input
                  id="bundle-path"
                  placeholder="/path/to/bundle.tar.gz"
                  value={formData.bundle_path || ""}
                  onChange={(e) => updateFormData({ bundle_path: e.target.value })}
                />
                <p className="text-xs text-muted-foreground mt-1">
                  The bundle must be signed with your publisher key
                </p>
              </div>
            </div>
          )}

          {currentStep === 2 && (
            <div className="space-y-4">
              <div>
                <h3 className="text-lg font-semibold mb-1">Choose Broker</h3>
                <p className="text-sm text-muted-foreground">
                  Select the marketplace to publish to
                </p>
              </div>
              <MarketplaceBrokerSelector
                brokers={brokers}
                selected={formData.broker}
                onChange={(broker) => updateFormData({ broker })}
              />
            </div>
          )}

          {currentStep === 3 && (
            <div className="space-y-4">
              <div>
                <h3 className="text-lg font-semibold mb-1">Bundle Metadata</h3>
                <p className="text-sm text-muted-foreground">
                  Add optional information about your bundle
                </p>
              </div>

              <div>
                <label htmlFor="description" className="block text-sm font-medium mb-2">
                  Description
                </label>
                <Textarea
                  id="description"
                  placeholder="Describe what your bundle does..."
                  value={formData.description || ""}
                  onChange={(e) => updateFormData({ description: e.target.value })}
                  rows={4}
                />
              </div>

              <div>
                <label htmlFor="homepage" className="block text-sm font-medium mb-2">
                  Homepage URL (optional)
                </label>
                <Input
                  id="homepage"
                  type="url"
                  placeholder="https://example.com"
                  value={formData.homepage || ""}
                  onChange={(e) => updateFormData({ homepage: e.target.value })}
                />
              </div>

              <div>
                <label htmlFor="repository" className="block text-sm font-medium mb-2">
                  Repository URL (optional)
                </label>
                <Input
                  id="repository"
                  type="url"
                  placeholder="https://github.com/user/repo"
                  value={formData.repository || ""}
                  onChange={(e) => updateFormData({ repository: e.target.value })}
                />
              </div>

              <div>
                <label htmlFor="tags" className="block text-sm font-medium mb-2">
                  Tags
                </label>
                <div className="flex gap-2 mb-2">
                  <Input
                    id="tags"
                    placeholder="Add tag..."
                    value={tagInput}
                    onChange={(e) => setTagInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        e.preventDefault();
                        handleAddTag();
                      }
                    }}
                  />
                  <Button
                    type="button"
                    variant="outline"
                    onClick={handleAddTag}
                    disabled={!tagInput.trim()}
                  >
                    Add
                  </Button>
                </div>
                {formData.tags && formData.tags.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {formData.tags.map((tag) => (
                      <Badge
                        key={tag}
                        variant="secondary"
                        className="cursor-pointer"
                        onClick={() => handleRemoveTag(tag)}
                      >
                        {tag} ×
                      </Badge>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {currentStep === 4 && (
            <div className="space-y-4">
              <div>
                <h3 className="text-lg font-semibold mb-1">Review & Confirm</h3>
                <p className="text-sm text-muted-foreground">
                  Please review your submission before publishing
                </p>
              </div>

              <div className="space-y-3">
                <div className="flex justify-between py-2 border-b">
                  <span className="text-sm font-medium">Bundle Path:</span>
                  <span className="text-sm text-muted-foreground font-mono">
                    {formData.bundle_path}
                  </span>
                </div>
                <div className="flex justify-between py-2 border-b">
                  <span className="text-sm font-medium">Broker:</span>
                  <span className="text-sm capitalize">{formData.broker}</span>
                </div>
                {formData.description && (
                  <div className="py-2 border-b">
                    <span className="text-sm font-medium">Description:</span>
                    <p className="text-sm text-muted-foreground mt-1">
                      {formData.description}
                    </p>
                  </div>
                )}
                {formData.homepage && (
                  <div className="flex justify-between py-2 border-b">
                    <span className="text-sm font-medium">Homepage:</span>
                    <a
                      href={formData.homepage}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm text-primary hover:underline"
                    >
                      {formData.homepage}
                    </a>
                  </div>
                )}
                {formData.repository && (
                  <div className="flex justify-between py-2 border-b">
                    <span className="text-sm font-medium">Repository:</span>
                    <a
                      href={formData.repository}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm text-primary hover:underline"
                    >
                      {formData.repository}
                    </a>
                  </div>
                )}
                {formData.tags && formData.tags.length > 0 && (
                  <div className="py-2">
                    <span className="text-sm font-medium">Tags:</span>
                    <div className="flex flex-wrap gap-1.5 mt-2">
                      {formData.tags.map((tag) => (
                        <Badge key={tag} variant="secondary">
                          {tag}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </Card>

      {/* Actions */}
      <div className="flex items-center justify-between">
        <Button
          variant="outline"
          onClick={currentStep === 1 ? onCancel : handleBack}
          disabled={isPublishing}
        >
          <ChevronLeft className="h-4 w-4 mr-2" />
          {currentStep === 1 ? "Cancel" : "Back"}
        </Button>

        {currentStep < STEPS.length ? (
          <Button
            onClick={handleNext}
            disabled={!canProceed() || isPublishing}
          >
            Next
            <ChevronRight className="h-4 w-4 ml-2" />
          </Button>
        ) : (
          <Button
            onClick={handleSubmit}
            disabled={!canProceed() || isPublishing}
          >
            {isPublishing ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Publishing...
              </>
            ) : (
              <>
                <Upload className="h-4 w-4 mr-2" />
                Publish Bundle
              </>
            )}
          </Button>
        )}
      </div>
    </div>
  );
}
