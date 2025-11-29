/**
 * MCP Server Types for SkillMeat Web UI
 *
 * These types represent MCP servers and deployment configurations
 */

export type MCPServerStatus = 'installed' | 'not_installed' | 'updating' | 'error';

export type DeploymentHealth = 'healthy' | 'unhealthy' | 'unknown';

export interface MCPServer {
  name: string;
  repo: string;
  version: string;
  description?: string;
  env_vars: Record<string, string>;
  status: MCPServerStatus;
  installed_at?: string;
  resolved_sha?: string;
  resolved_version?: string;
  last_updated?: string;
}

export interface MCPServerListResponse {
  servers: MCPServer[];
  total: number;
}

export interface DeploymentStatus {
  deployed: boolean;
  settings_path?: string;
  last_deployed?: string;
  health_status?: DeploymentHealth;
  command?: string;
  args?: string[];
}

export interface DeploymentRequest {
  dry_run?: boolean;
  backup?: boolean;
}

export interface DeploymentResponse {
  success: boolean;
  message: string;
  settings_path?: string;
  backup_path?: string;
  env_file_path?: string;
  command?: string;
  args?: string[];
  error_message?: string;
}

export interface MCPServerCreateRequest {
  name: string;
  repo: string;
  version?: string;
  description?: string;
  env_vars?: Record<string, string>;
}

export interface MCPServerUpdateRequest {
  repo?: string;
  version?: string;
  description?: string;
  env_vars?: Record<string, string>;
}

export interface MCPServerFilters {
  status?: MCPServerStatus | 'all';
  search?: string;
}

export type MCPSortField = 'name' | 'status' | 'last_updated';
export type MCPSortOrder = 'asc' | 'desc';

export interface MCPServerSort {
  field: MCPSortField;
  order: MCPSortOrder;
}

// Form validation helpers
export interface EnvVarEntry {
  key: string;
  value: string;
  required?: boolean;
}

export interface MCPFormData {
  name: string;
  repo: string;
  version: string;
  description: string;
  env_vars: EnvVarEntry[];
}

// UI state types
export interface MCPUIState {
  selectedServer?: MCPServer;
  isDeploying: boolean;
  deploymentProgress?: string;
  filters: MCPServerFilters;
  sort: MCPServerSort;
}
