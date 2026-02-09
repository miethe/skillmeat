/**
 * Project Types for SkillMeat Projects View
 *
 * These types represent projects with deployed artifacts from collections.
 */
import { Platform } from './enums';

export interface DeployedArtifact {
  artifact_name: string;
  artifact_type: 'skill' | 'command' | 'agent' | 'mcp' | 'hook';
  from_collection: string;
  deployed_at: string;
  artifact_path: string;
  version?: string;
  collection_sha: string;
  local_modifications: boolean;
  deployment_profile_id?: string;
  platform?: Platform;
  profile_root_dir?: string;
}

export interface ProjectStats {
  by_type: Record<string, number>;
  by_collection: Record<string, number>;
  by_profile?: Record<string, number>;
  modified_count: number;
}

export interface DeploymentProfileInfo {
  profile_id: string;
  platform: Platform;
  root_dir: string;
  artifact_path_map: Record<string, string>;
  context_path_prefixes: string[];
}

export interface ProjectSummary {
  id: string;
  path: string;
  name: string;
  deployment_count: number;
  last_deployment?: string;
}

export interface ProjectDetail extends ProjectSummary {
  deployments: DeployedArtifact[];
  stats: ProjectStats;
  deployment_profiles?: DeploymentProfileInfo[];
}

export interface ProjectsResponse {
  items: ProjectSummary[];
  page_info: {
    has_next_page: boolean;
    has_previous_page: boolean;
    start_cursor: string | null;
    end_cursor: string | null;
    total_count: number;
  };
}

export interface ProjectDetailResponse {
  id: string;
  path: string;
  name: string;
  deployment_count: number;
  last_deployment?: string;
  deployments: DeployedArtifact[];
  stats: ProjectStats;
  deployment_profiles?: DeploymentProfileInfo[];
}
