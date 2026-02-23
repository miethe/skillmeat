'use client';

import * as React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { Settings, Github, MonitorCog, Layers, Plus, Info } from 'lucide-react';
import { GitHubSettings } from '@/components/settings/github-settings';
import { PlatformDefaultsSettings } from '@/components/settings/platform-defaults-settings';
import { CustomContextSettings } from '@/components/settings/custom-context-settings';
import { CreateProfileForm } from '@/components/profiles';
import { useCreateDeploymentProfile } from '@/hooks';
import { useToast } from '@/hooks';
import type { CreateDeploymentProfileRequest } from '@/types/deployments';

export default function SettingsPage() {
  const [newProfileOpen, setNewProfileOpen] = React.useState(false);
  const [isSubmitting, setIsSubmitting] = React.useState(false);

  const { toast } = useToast();

  // Deployment profiles are project-scoped; from Settings (no project context),
  // we show an informational note rather than a broken create flow.
  // useCreateDeploymentProfile(undefined) is kept here for completeness but
  // is not invoked without a projectId.
  const createProfile = useCreateDeploymentProfile(undefined);

  const handleCreateProfile = React.useCallback(
    async (data: CreateDeploymentProfileRequest) => {
      setIsSubmitting(true);
      try {
        await createProfile.mutateAsync(data);
        toast({
          title: 'Profile created',
          description: `Deployment profile "${data.profile_id}" created successfully.`,
        });
        setNewProfileOpen(false);
      } catch (error) {
        toast({
          title: 'Failed to create profile',
          description: error instanceof Error ? error.message : 'An error occurred',
          variant: 'destructive',
        });
      } finally {
        setIsSubmitting(false);
      }
    },
    [createProfile, toast]
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
        <p className="text-muted-foreground">Configure SkillMeat preferences and integrations</p>
      </div>

      <Tabs defaultValue="general">
        <TabsList className="mb-4">
          <TabsTrigger value="general" className="flex items-center gap-2">
            <Settings className="h-4 w-4" />
            General
          </TabsTrigger>
          <TabsTrigger value="integrations" className="flex items-center gap-2">
            <Github className="h-4 w-4" />
            Integrations
          </TabsTrigger>
          <TabsTrigger value="context" className="flex items-center gap-2">
            <Layers className="h-4 w-4" />
            Context
          </TabsTrigger>
          <TabsTrigger value="platforms" className="flex items-center gap-2">
            <MonitorCog className="h-4 w-4" />
            Platforms
          </TabsTrigger>
        </TabsList>

        {/* General Tab */}
        <TabsContent value="general" className="space-y-4">
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Settings className="h-5 w-5" />
                <CardTitle>General Settings</CardTitle>
              </div>
              <CardDescription>Application preferences and defaults</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                Configure default scope, GitHub authentication, and other general settings.
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>API Configuration</CardTitle>
              <CardDescription>Backend connection settings</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">API URL</span>
                  <span className="text-sm text-muted-foreground">
                    {process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080'}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">Version</span>
                  <span className="text-sm text-muted-foreground">
                    {process.env.NEXT_PUBLIC_APP_VERSION || '0.3.0-alpha'}
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Integrations Tab */}
        <TabsContent value="integrations" className="space-y-4">
          <GitHubSettings />
        </TabsContent>

        {/* Context Tab */}
        <TabsContent value="context" className="space-y-4">
          <CustomContextSettings />
        </TabsContent>

        {/* Platforms Tab */}
        <TabsContent value="platforms" className="space-y-4">
          <PlatformDefaultsSettings />

          {/* Project-scoped profile info note */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Info className="h-5 w-5 text-muted-foreground" />
                <CardTitle className="text-base">Custom Deployment Profiles</CardTitle>
              </div>
              <CardDescription>
                Deployment profiles are scoped to individual projects. To create or manage
                profiles for a specific project, open that project&apos;s settings page.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button
                variant="outline"
                onClick={() => setNewProfileOpen(true)}
              >
                <Plus className="mr-2 h-4 w-4" />
                New Custom Profile
              </Button>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* New Custom Profile Dialog */}
      <Dialog open={newProfileOpen} onOpenChange={setNewProfileOpen}>
        <DialogContent className="max-h-[90vh] max-w-2xl overflow-y-auto">
          <DialogHeader>
            <DialogTitle>New Custom Profile</DialogTitle>
            <DialogDescription>
              Create a new deployment profile. Note: profiles are project-scoped and will need
              to be associated with a project after creation.
            </DialogDescription>
          </DialogHeader>
          <CreateProfileForm
            contextMode="dialog"
            isSubmitting={isSubmitting}
            onSubmit={handleCreateProfile}
            onCancel={() => setNewProfileOpen(false)}
          />
        </DialogContent>
      </Dialog>
    </div>
  );
}
