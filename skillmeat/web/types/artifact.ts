/**
 * Artifact Types for SkillMeat Collection
 *
 * These types represent artifacts in the collection (Skills, Commands, Agents, MCP servers, Hooks)
 */

import { Tool } from './enums';

export type ArtifactType = 'skill' | 'command' | 'agent' | 'mcp' | 'hook';

export type ArtifactScope = 'user' | 'local';

export type ArtifactStatus = 'active' | 'outdated' | 'conflict' | 'error';

export interface ArtifactMetadata {
  title?: string;
  description?: string;
  license?: string;
  author?: string;
  version?: string;
  tags?: string[];
  tools?: Tool[];  // Claude Code tools used by this artifact
}

export interface UpstreamStatus {
  hasUpstream: boolean;
  upstreamUrl?: string;
  upstreamVersion?: string;
  currentVersion?: string;
  isOutdated: boolean;
  lastChecked?: string;
}

export interface UsageStats {
  totalDeployments: number;
  activeProjects: number;
  lastUsed?: string;
  usageCount: number;
}

export interface ArtifactScore {
  confidence: number;
  trustScore?: number;
  qualityScore?: number;
  matchScore?: number;
  lastUpdated?: string;
}

export interface Artifact {
  id: string;
  name: string;
  type: ArtifactType;
  scope: ArtifactScope;
  status: ArtifactStatus;
  version?: string;
  source?: string;
  /** Origin category: 'local', 'github', or 'marketplace' */
  origin?: string;
  /** Platform source when origin is 'marketplace' (e.g., 'github', 'gitlab', 'bitbucket') */
  origin_source?: string;
  metadata: ArtifactMetadata;
  upstreamStatus: UpstreamStatus;
  usageStats: UsageStats;
  createdAt: string;
  updatedAt: string;
  aliases?: string[];
  collection?: {
    id: string;
    name: string;
  };
  /**
   * All collections this artifact belongs to (many-to-many relationship)
   * TODO: Backend needs to populate this field with data from CollectionArtifact table
   */
  collections?: {
    id: string;
    name: string;
    artifact_count?: number;
  }[];
  score?: ArtifactScore;
}

export interface ArtifactFilters {
  type?: ArtifactType | 'all';
  status?: ArtifactStatus | 'all';
  scope?: ArtifactScope | 'all';
  search?: string;
  /** Group ID for filtering artifacts by group (only applicable in specific collection context) */
  groupId?: string;
  /** Tag IDs to filter artifacts by (multi-select) */
  tags?: string[];
  /** Tool names to filter artifacts by (multi-select) */
  tools?: string[];
}

export type SortField = 'name' | 'updatedAt' | 'usageCount' | 'confidence';
export type SortOrder = 'asc' | 'desc';

export interface ArtifactSort {
  field: SortField;
  order: SortOrder;
}

export interface ArtifactsResponse {
  artifacts: Artifact[];
  total: number;
  page: number;
  pageSize: number;
}
