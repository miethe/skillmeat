/**
 * Central export point for all TypeScript type definitions
 *
 * IMPORTANT: This barrel export uses `export *` which can cause conflicts
 * when multiple modules export types with the same name (PageInfo, ImportResult, etc.).
 *
 * Resolution strategy:
 * - artifact.ts is the authoritative source for Artifact and Entity types
 * - entity.ts is NOT re-exported here (import directly from '@/types/entity' if needed)
 * - For conflicting types, import directly from the specific module
 *
 * Duplicate type names (import from specific module if needed):
 * - PageInfo: analytics, marketplace, context-entity, template
 * - ImportResult: bundle, discovery, marketplace, notification
 * - ImportRequest: bundle, marketplace
 * - ImportStatus: discovery, notification
 */

// Core artifact types (includes Entity backward-compat aliases)
export * from './artifact';

// Entity module - NOT exported via barrel to avoid conflicts with artifact.ts
// Import directly: import { ENTITY_TYPES, getEntityTypeConfig } from '@/types/entity';

// Enums (shared across modules)
export * from './enums';

// File operations
export * from './files';

// Analytics
export * from './analytics';

// Bundle operations
export * from './bundle';

// Discovery types
export * from './discovery';

// Marketplace types
export * from './marketplace';

// MCP types
export * from './mcp';

// Notification types
export * from './notification';

// Project types
export * from './project';

// Version types
export * from './version';
export * from './history';

// Drift detection types
export * from './drift';

// Sync types
export * from './sync';

// Collections navigation types (Phase 3)
export * from './collections';
export * from './groups';
export * from './deployments';

// Context entities (Agent Context Entities v1)
export * from './context-entity';

// Path-based tag extraction (Phase 1)
export * from './path-tags';

// Deployment sets (DS-009)
export * from './deployment-sets';

// Similar artifacts (feat/similar-artifacts)
export * from './similarity';

// Workflow orchestration types
export * from './workflow';
