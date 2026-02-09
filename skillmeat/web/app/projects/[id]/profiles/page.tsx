'use client';

import { useMemo, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { ArrowLeft, Plus, Save, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useToast, useProject, useDeploymentProfiles, useCreateDeploymentProfile, useUpdateDeploymentProfile, useDeleteDeploymentProfile } from '@/hooks';
import { PlatformBadge } from '@/components/platform-badge';
import { Platform } from '@/types/enums';
import type {
  CreateDeploymentProfileRequest,
  DeploymentProfile,
  UpdateDeploymentProfileRequest,
} from '@/types/deployments';

type ProfileFormState = {
  profile_id: string;
  platform: Platform;
  root_dir: string;
  artifact_path_map_json: string;
  project_config_filenames: string;
  context_path_prefixes: string;
  supported_artifact_types: string;
};

function toList(value: string): string[] {
  return value
    .split(/[\n,]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function defaultRootDir(platform: Platform): string {
  switch (platform) {
    case Platform.CODEX:
      return '.codex';
    case Platform.GEMINI:
      return '.gemini';
    case Platform.CURSOR:
      return '.cursor';
    case Platform.CLAUDE_CODE:
      return '.claude';
    default:
      return '.custom';
  }
}

function profileToForm(profile: DeploymentProfile): ProfileFormState {
  return {
    profile_id: profile.profile_id,
    platform: profile.platform,
    root_dir: profile.root_dir,
    artifact_path_map_json: JSON.stringify(profile.artifact_path_map || {}, null, 2),
    project_config_filenames: (profile.project_config_filenames || []).join('\n'),
    context_path_prefixes: (profile.context_path_prefixes || []).join('\n'),
    supported_artifact_types: (profile.supported_artifact_types || []).join(', '),
  };
}

function parseCreatePayload(form: ProfileFormState): CreateDeploymentProfileRequest {
  return {
    profile_id: form.profile_id.trim(),
    platform: form.platform,
    root_dir: form.root_dir.trim(),
    artifact_path_map: JSON.parse(form.artifact_path_map_json || '{}'),
    project_config_filenames: toList(form.project_config_filenames),
    context_path_prefixes: toList(form.context_path_prefixes),
    supported_artifact_types: toList(form.supported_artifact_types),
  };
}

function parseUpdatePayload(form: ProfileFormState): UpdateDeploymentProfileRequest {
  return {
    platform: form.platform,
    root_dir: form.root_dir.trim(),
    artifact_path_map: JSON.parse(form.artifact_path_map_json || '{}'),
    project_config_filenames: toList(form.project_config_filenames),
    context_path_prefixes: toList(form.context_path_prefixes),
    supported_artifact_types: toList(form.supported_artifact_types),
  };
}

export default function ProjectProfilesPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.id as string;
  const { toast } = useToast();

  const { data: project } = useProject(projectId);
  const { data: profiles = [], isLoading } = useDeploymentProfiles(projectId);
  const createProfile = useCreateDeploymentProfile(projectId);
  const updateProfile = useUpdateDeploymentProfile(projectId);
  const deleteProfile = useDeleteDeploymentProfile(projectId);

  const [createForm, setCreateForm] = useState<ProfileFormState>({
    profile_id: '',
    platform: Platform.CLAUDE_CODE,
    root_dir: '.claude',
    artifact_path_map_json: '{}',
    project_config_filenames: 'CLAUDE.md',
    context_path_prefixes: '.claude/context/\n.claude/',
    supported_artifact_types: 'skill, command, agent, hook, mcp',
  });
  const [editingProfileId, setEditingProfileId] = useState<string | null>(null);
  const [editForm, setEditForm] = useState<ProfileFormState | null>(null);

  const profileCountLabel = useMemo(() => `${profiles.length} profile(s) configured`, [profiles.length]);

  const handleCreate = async () => {
    try {
      await createProfile.mutateAsync(parseCreatePayload(createForm));
      toast({
        title: 'Profile created',
        description: `Created profile "${createForm.profile_id}"`,
      });
      setCreateForm((prev) => ({
        ...prev,
        profile_id: '',
      }));
    } catch (error) {
      toast({
        title: 'Failed to create profile',
        description: error instanceof Error ? error.message : 'Invalid profile payload',
        variant: 'destructive',
      });
    }
  };

  const startEdit = (profile: DeploymentProfile) => {
    setEditingProfileId(profile.profile_id);
    setEditForm(profileToForm(profile));
  };

  const handleSaveEdit = async () => {
    if (!editingProfileId || !editForm) return;
    try {
      await updateProfile.mutateAsync({
        profileId: editingProfileId,
        data: parseUpdatePayload(editForm),
      });
      toast({
        title: 'Profile updated',
        description: `Updated profile "${editingProfileId}"`,
      });
      setEditingProfileId(null);
      setEditForm(null);
    } catch (error) {
      toast({
        title: 'Failed to update profile',
        description: error instanceof Error ? error.message : 'Invalid profile update payload',
        variant: 'destructive',
      });
    }
  };

  const handleDelete = async (profileId: string) => {
    try {
      await deleteProfile.mutateAsync(profileId);
      toast({
        title: 'Profile deleted',
        description: `Deleted profile "${profileId}"`,
      });
    } catch (error) {
      toast({
        title: 'Failed to delete profile',
        description: error instanceof Error ? error.message : 'Delete request failed',
        variant: 'destructive',
      });
    }
  };

  return (
    <div className="space-y-6 p-6">
      <div className="space-y-4">
        <Button variant="ghost" onClick={() => router.push(`/projects/${projectId}`)}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Project
        </Button>

        <div>
          <h1 className="text-3xl font-bold tracking-tight">Deployment Profiles</h1>
          <p className="text-sm text-muted-foreground">
            {project?.name ? `${project.name}: ` : ''}{profileCountLabel}
          </p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Create Profile</CardTitle>
          <CardDescription>Add a new platform profile and path mappings.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          <div className="space-y-2">
            <Label htmlFor="new-profile-id">Profile ID</Label>
            <Input
              id="new-profile-id"
              placeholder="codex-default"
              value={createForm.profile_id}
              onChange={(e) => setCreateForm((prev) => ({ ...prev, profile_id: e.target.value }))}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="new-platform">Platform</Label>
            <Select
              value={createForm.platform}
              onValueChange={(value) =>
                setCreateForm((prev) => ({
                  ...prev,
                  platform: value as Platform,
                  root_dir: defaultRootDir(value as Platform),
                }))
              }
            >
              <SelectTrigger id="new-platform">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={Platform.CLAUDE_CODE}>Claude Code</SelectItem>
                <SelectItem value={Platform.CODEX}>Codex</SelectItem>
                <SelectItem value={Platform.GEMINI}>Gemini</SelectItem>
                <SelectItem value={Platform.CURSOR}>Cursor</SelectItem>
                <SelectItem value={Platform.OTHER}>Other</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2 md:col-span-2">
            <Label htmlFor="new-root-dir">Root Dir</Label>
            <Input
              id="new-root-dir"
              value={createForm.root_dir}
              onChange={(e) => setCreateForm((prev) => ({ ...prev, root_dir: e.target.value }))}
            />
          </div>
          <div className="space-y-2 md:col-span-2">
            <Label htmlFor="new-artifact-map">Artifact Path Map (JSON)</Label>
            <Textarea
              id="new-artifact-map"
              rows={5}
              value={createForm.artifact_path_map_json}
              onChange={(e) =>
                setCreateForm((prev) => ({ ...prev, artifact_path_map_json: e.target.value }))
              }
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="new-configs">Config Filenames (newline/comma separated)</Label>
            <Textarea
              id="new-configs"
              rows={3}
              value={createForm.project_config_filenames}
              onChange={(e) =>
                setCreateForm((prev) => ({ ...prev, project_config_filenames: e.target.value }))
              }
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="new-context-prefixes">Context Prefixes (newline/comma separated)</Label>
            <Textarea
              id="new-context-prefixes"
              rows={3}
              value={createForm.context_path_prefixes}
              onChange={(e) =>
                setCreateForm((prev) => ({ ...prev, context_path_prefixes: e.target.value }))
              }
            />
          </div>
          <div className="space-y-2 md:col-span-2">
            <Label htmlFor="new-supported-types">Supported Artifact Types</Label>
            <Input
              id="new-supported-types"
              value={createForm.supported_artifact_types}
              onChange={(e) =>
                setCreateForm((prev) => ({ ...prev, supported_artifact_types: e.target.value }))
              }
            />
          </div>
          <div className="md:col-span-2">
            <Button
              onClick={handleCreate}
              disabled={createProfile.isPending || !createForm.profile_id.trim()}
            >
              <Plus className="mr-2 h-4 w-4" />
              Create Profile
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Configured Profiles</CardTitle>
          <CardDescription>Edit profile mappings and path roots for this project.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {isLoading ? (
            <p className="text-sm text-muted-foreground">Loading profiles...</p>
          ) : profiles.length === 0 ? (
            <p className="text-sm text-muted-foreground">No deployment profiles found.</p>
          ) : (
            profiles.map((profile) => {
              const isEditing = editingProfileId === profile.profile_id && editForm;
              return (
                <div key={profile.profile_id} className="rounded-lg border p-4">
                  {isEditing ? (
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <p className="font-medium">{profile.profile_id}</p>
                        <PlatformBadge platform={editForm.platform} compact />
                      </div>
                      <div className="grid gap-3 md:grid-cols-2">
                        <div className="space-y-2">
                          <Label>Platform</Label>
                          <Select
                            value={editForm.platform}
                            onValueChange={(value) =>
                              setEditForm((prev) =>
                                prev ? { ...prev, platform: value as Platform } : prev
                              )
                            }
                          >
                            <SelectTrigger>
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value={Platform.CLAUDE_CODE}>Claude Code</SelectItem>
                              <SelectItem value={Platform.CODEX}>Codex</SelectItem>
                              <SelectItem value={Platform.GEMINI}>Gemini</SelectItem>
                              <SelectItem value={Platform.CURSOR}>Cursor</SelectItem>
                              <SelectItem value={Platform.OTHER}>Other</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                        <div className="space-y-2">
                          <Label>Root Dir</Label>
                          <Input
                            value={editForm.root_dir}
                            onChange={(e) =>
                              setEditForm((prev) =>
                                prev ? { ...prev, root_dir: e.target.value } : prev
                              )
                            }
                          />
                        </div>
                      </div>
                      <div className="space-y-2">
                        <Label>Artifact Path Map (JSON)</Label>
                        <Textarea
                          rows={4}
                          value={editForm.artifact_path_map_json}
                          onChange={(e) =>
                            setEditForm((prev) =>
                              prev ? { ...prev, artifact_path_map_json: e.target.value } : prev
                            )
                          }
                        />
                      </div>
                      <div className="flex items-center gap-2">
                        <Button onClick={handleSaveEdit} disabled={updateProfile.isPending}>
                          <Save className="mr-2 h-4 w-4" />
                          Save
                        </Button>
                        <Button
                          variant="outline"
                          onClick={() => {
                            setEditingProfileId(null);
                            setEditForm(null);
                          }}
                        >
                          Cancel
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="font-medium">{profile.profile_id}</p>
                          <p className="text-xs text-muted-foreground">{profile.root_dir}</p>
                        </div>
                        <PlatformBadge platform={profile.platform} compact />
                      </div>
                      <div className="rounded bg-muted/30 p-2 text-xs">
                        <pre className="whitespace-pre-wrap">{JSON.stringify(profile.artifact_path_map, null, 2)}</pre>
                      </div>
                      <div className="flex items-center gap-2">
                        <Button variant="outline" size="sm" onClick={() => startEdit(profile)}>
                          Edit
                        </Button>
                        <Button
                          variant="destructive"
                          size="sm"
                          onClick={() => handleDelete(profile.profile_id)}
                          disabled={deleteProfile.isPending}
                        >
                          <Trash2 className="mr-2 h-4 w-4" />
                          Delete
                        </Button>
                      </div>
                    </div>
                  )}
                </div>
              );
            })
          )}
        </CardContent>
      </Card>
    </div>
  );
}
