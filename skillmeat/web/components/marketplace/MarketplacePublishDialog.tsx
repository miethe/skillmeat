"use client";

import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import { usePublishBundle } from "@/hooks/useMarketplace";
import { useToast } from "@/hooks/use-toast";
import type { ArtifactCategory } from "@/types/marketplace";
import { X, Info } from "lucide-react";

interface MarketplacePublishDialogProps {
  bundlePath: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

const ARTIFACT_CATEGORIES: { value: ArtifactCategory; label: string }[] = [
  { value: "skill", label: "Skill" },
  { value: "command", label: "Command" },
  { value: "agent", label: "Agent" },
  { value: "hook", label: "Hook" },
  { value: "mcp-server", label: "MCP Server" },
  { value: "bundle", label: "Bundle" },
];

const LICENSES = ["MIT", "Apache-2.0", "GPL-3.0", "BSD-3-Clause", "ISC", "Other"];

const SUGGESTED_TAGS = [
  "documentation",
  "productivity",
  "code-review",
  "testing",
  "deployment",
  "analytics",
  "security",
  "database",
  "ai",
  "automation",
];

export function MarketplacePublishDialog({
  bundlePath,
  open,
  onOpenChange,
  onSuccess,
}: MarketplacePublishDialogProps) {
  const [formData, setFormData] = useState({
    name: "",
    description: "",
    category: "bundle" as ArtifactCategory,
    version: "1.0.0",
    license: "MIT",
    tags: [] as string[],
    homepage: "",
    repository: "",
    price: 0,
    sign_bundle: true,
  });

  const [customTag, setCustomTag] = useState("");

  const { mutate: publishBundle, isPending: isPublishing } = usePublishBundle();
  const { toast } = useToast();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    // Validation
    if (!formData.name.trim()) {
      toast({
        title: "Validation error",
        description: "Name is required",
        variant: "destructive",
      });
      return;
    }

    if (!formData.description.trim()) {
      toast({
        title: "Validation error",
        description: "Description is required",
        variant: "destructive",
      });
      return;
    }

    publishBundle(
      {
        bundle_path: bundlePath,
        name: formData.name,
        description: formData.description,
        category: formData.category,
        version: formData.version,
        license: formData.license,
        tags: formData.tags,
        homepage: formData.homepage || undefined,
        repository: formData.repository || undefined,
        price: formData.price,
        sign_bundle: formData.sign_bundle,
      },
      {
        onSuccess: (data) => {
          toast({
            title: "Bundle published successfully",
            description: data.message,
          });
          onOpenChange(false);
          onSuccess?.();
        },
        onError: (error) => {
          toast({
            title: "Publication failed",
            description: error.message,
            variant: "destructive",
          });
        },
      }
    );
  };

  const addCustomTag = () => {
    const tag = customTag.trim().toLowerCase();
    if (tag && !formData.tags.includes(tag)) {
      setFormData({ ...formData, tags: [...formData.tags, tag] });
      setCustomTag("");
    }
  };

  const removeTag = (tagToRemove: string) => {
    setFormData({ ...formData, tags: formData.tags.filter((tag) => tag !== tagToRemove) });
  };

  const toggleSuggestedTag = (tag: string) => {
    if (formData.tags.includes(tag)) {
      removeTag(tag);
    } else {
      setFormData({ ...formData, tags: [...formData.tags, tag] });
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-[600px]">
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>Publish to Marketplace</DialogTitle>
            <DialogDescription>
              Share your bundle with the SkillMeat community. Fill in the details below.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            {/* Name */}
            <div className="space-y-2">
              <Label htmlFor="name">
                Name <span className="text-destructive">*</span>
              </Label>
              <Input
                id="name"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="my-awesome-bundle"
                required
              />
            </div>

            {/* Description */}
            <div className="space-y-2">
              <Label htmlFor="description">
                Description <span className="text-destructive">*</span>
              </Label>
              <Textarea
                id="description"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="A brief description of what this bundle does..."
                rows={4}
                required
              />
            </div>

            {/* Category and Version */}
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="category">Category</Label>
                <select
                  id="category"
                  value={formData.category}
                  onChange={(e) =>
                    setFormData({ ...formData, category: e.target.value as ArtifactCategory })
                  }
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {ARTIFACT_CATEGORIES.map((cat) => (
                    <option key={cat.value} value={cat.value}>
                      {cat.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="version">Version</Label>
                <Input
                  id="version"
                  value={formData.version}
                  onChange={(e) => setFormData({ ...formData, version: e.target.value })}
                  placeholder="1.0.0"
                />
              </div>
            </div>

            {/* License */}
            <div className="space-y-2">
              <Label htmlFor="license">License</Label>
              <select
                id="license"
                value={formData.license}
                onChange={(e) => setFormData({ ...formData, license: e.target.value })}
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {LICENSES.map((license) => (
                  <option key={license} value={license}>
                    {license}
                  </option>
                ))}
              </select>
            </div>

            {/* Tags */}
            <div className="space-y-2">
              <Label>Tags</Label>
              <div className="space-y-3">
                {/* Selected Tags */}
                {formData.tags.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {formData.tags.map((tag) => (
                      <Badge key={tag} variant="secondary" className="gap-1">
                        {tag}
                        <button
                          type="button"
                          onClick={() => removeTag(tag)}
                          className="ml-1 hover:text-destructive"
                          aria-label={`Remove ${tag} tag`}
                        >
                          <X className="h-3 w-3" />
                        </button>
                      </Badge>
                    ))}
                  </div>
                )}

                {/* Suggested Tags */}
                <div className="flex flex-wrap gap-2">
                  {SUGGESTED_TAGS.map((tag) => {
                    const isSelected = formData.tags.includes(tag);
                    return (
                      <button
                        key={tag}
                        type="button"
                        onClick={() => toggleSuggestedTag(tag)}
                        className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                          isSelected
                            ? "bg-primary text-primary-foreground"
                            : "bg-secondary text-secondary-foreground hover:bg-secondary/80"
                        }`}
                      >
                        {tag}
                      </button>
                    );
                  })}
                </div>

                {/* Custom Tag Input */}
                <div className="flex gap-2">
                  <Input
                    value={customTag}
                    onChange={(e) => setCustomTag(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        e.preventDefault();
                        addCustomTag();
                      }
                    }}
                    placeholder="Add custom tag..."
                  />
                  <Button type="button" onClick={addCustomTag} variant="outline">
                    Add
                  </Button>
                </div>
              </div>
            </div>

            {/* Optional URLs */}
            <div className="space-y-2">
              <Label htmlFor="homepage">Homepage (optional)</Label>
              <Input
                id="homepage"
                type="url"
                value={formData.homepage}
                onChange={(e) => setFormData({ ...formData, homepage: e.target.value })}
                placeholder="https://example.com"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="repository">Repository (optional)</Label>
              <Input
                id="repository"
                type="url"
                value={formData.repository}
                onChange={(e) => setFormData({ ...formData, repository: e.target.value })}
                placeholder="https://github.com/username/repo"
              />
            </div>

            {/* Signing Option */}
            <div className="flex items-start space-x-2">
              <Checkbox
                id="sign-bundle"
                checked={formData.sign_bundle}
                onCheckedChange={(checked) =>
                  setFormData({ ...formData, sign_bundle: checked as boolean })
                }
              />
              <div className="grid gap-1.5 leading-none">
                <Label
                  htmlFor="sign-bundle"
                  className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                >
                  Sign bundle cryptographically
                </Label>
                <p className="text-xs text-muted-foreground">
                  Recommended for verified publishers to ensure bundle integrity
                </p>
              </div>
            </div>

            {/* Info Notice */}
            <div className="flex items-start gap-3 rounded-lg border bg-muted p-3">
              <Info className="mt-0.5 h-4 w-4 text-muted-foreground" />
              <div className="flex-1 space-y-1 text-xs text-muted-foreground">
                <p className="font-semibold">Publication Review:</p>
                <p>
                  Your bundle will be reviewed before appearing in the marketplace. This typically
                  takes 1-2 business days. You'll be notified when the review is complete.
                </p>
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={isPublishing}>
              {isPublishing ? "Publishing..." : "Publish"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
