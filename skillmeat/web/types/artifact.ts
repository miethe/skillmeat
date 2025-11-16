/**
 * Artifact Types for SkillMeat Collection
 *
 * These types represent artifacts in the collection (Skills, Commands, Agents, MCP servers, Hooks)
 */

export type ArtifactType = "skill" | "command" | "agent" | "mcp" | "hook";

export type ArtifactScope = "user" | "local";

export type ArtifactStatus = "active" | "outdated" | "conflict" | "error";

export interface ArtifactMetadata {
  title?: string;
  description?: string;
  license?: string;
  author?: string;
  version?: string;
  tags?: string[];
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

export interface Artifact {
  id: string;
  name: string;
  type: ArtifactType;
  scope: ArtifactScope;
  status: ArtifactStatus;
  version?: string;
  source?: string;
  metadata: ArtifactMetadata;
  upstreamStatus: UpstreamStatus;
  usageStats: UsageStats;
  createdAt: string;
  updatedAt: string;
  aliases?: string[];
}

export interface ArtifactFilters {
  type?: ArtifactType | "all";
  status?: ArtifactStatus | "all";
  scope?: ArtifactScope | "all";
  search?: string;
}

export type SortField = "name" | "updatedAt" | "usageCount";
export type SortOrder = "asc" | "desc";

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
