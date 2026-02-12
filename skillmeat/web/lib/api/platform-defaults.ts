/**
 * Platform defaults and custom context API service functions
 */
import { apiRequest } from '@/lib/api';

// ---------------------------------------------------------------------------
// Types (matching backend Pydantic schemas in platform_defaults.py)
// ---------------------------------------------------------------------------

export interface PlatformDefaultsEntry {
  root_dir: string;
  artifact_path_map: Record<string, string>;
  config_filenames: string[];
  supported_artifact_types: string[];
  context_prefixes: string[];
}

export interface PlatformDefaultsResponse extends PlatformDefaultsEntry {
  platform: string;
}

export interface AllPlatformDefaultsResponse {
  defaults: Record<string, PlatformDefaultsEntry>;
}

export interface PlatformDefaultsUpdateRequest {
  root_dir?: string;
  artifact_path_map?: Record<string, string>;
  config_filenames?: string[];
  supported_artifact_types?: string[];
  context_prefixes?: string[];
}

export interface CustomContextConfig {
  enabled: boolean;
  prefixes: string[];
  mode: 'override' | 'addendum';
  platforms: string[];
}

export interface CustomContextConfigUpdateRequest {
  enabled?: boolean;
  prefixes?: string[];
  mode?: 'override' | 'addendum';
  platforms?: string[];
}

// ---------------------------------------------------------------------------
// Platform Defaults API
// ---------------------------------------------------------------------------

export async function getAllPlatformDefaults(): Promise<AllPlatformDefaultsResponse> {
  return apiRequest<AllPlatformDefaultsResponse>('/settings/platform-defaults');
}

export async function getPlatformDefault(platform: string): Promise<PlatformDefaultsResponse> {
  return apiRequest<PlatformDefaultsResponse>(`/settings/platform-defaults/${platform}`);
}

export async function updatePlatformDefault(
  platform: string,
  data: PlatformDefaultsUpdateRequest
): Promise<PlatformDefaultsResponse> {
  return apiRequest<PlatformDefaultsResponse>(`/settings/platform-defaults/${platform}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function resetPlatformDefault(platform: string): Promise<PlatformDefaultsResponse> {
  return apiRequest<PlatformDefaultsResponse>(`/settings/platform-defaults/${platform}`, {
    method: 'DELETE',
  });
}

// ---------------------------------------------------------------------------
// Custom Context API
// ---------------------------------------------------------------------------

export async function getCustomContextConfig(): Promise<CustomContextConfig> {
  return apiRequest<CustomContextConfig>('/settings/custom-context');
}

export async function updateCustomContextConfig(
  data: CustomContextConfigUpdateRequest
): Promise<CustomContextConfig> {
  return apiRequest<CustomContextConfig>('/settings/custom-context', {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}
