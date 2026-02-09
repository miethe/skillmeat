import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Settings } from 'lucide-react';
import { GitHubSettings } from '@/components/settings/github-settings';
import { PlatformDefaultsSettings } from '@/components/settings/platform-defaults-settings';
import { CustomContextSettings } from '@/components/settings/custom-context-settings';

export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
        <p className="text-muted-foreground">Configure SkillMeat preferences and integrations</p>
      </div>

      <div className="space-y-4">
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

        <GitHubSettings />
        <PlatformDefaultsSettings />
        <CustomContextSettings />
      </div>
    </div>
  );
}
