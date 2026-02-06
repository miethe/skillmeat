/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ContextEntityType } from './ContextEntityType';
/**
 * Request schema for creating a context entity.
 *
 * Context entities are artifacts with special roles in Claude Code projects.
 * They support path-pattern matching for auto-loading and categorization.
 *
 * Path Pattern Security:
 * - Must start with '.claude/' (enforced via validation)
 * - Cannot contain '..' for path traversal prevention
 *
 * Examples:
 * >>> # Rule file that auto-loads for web path edits
 * >>> request = ContextEntityCreateRequest(
 * ...     name="web-hooks-rules",
 * ...     entity_type=ContextEntityType.RULE_FILE,
 * ...     content="# Web Hooks Patterns\n...",
 * ...     path_pattern=".claude/rules/web/hooks.md",
 * ...     category="web",
 * ...     auto_load=True
 * ... )
 */
export type ContextEntityCreateRequest = {
  /**
   * Human-readable name for the context entity
   */
  name: string;
  /**
   * Type of context entity (determines role and conventions)
   */
  entity_type: ContextEntityType;
  /**
   * Markdown content of the context entity
   */
  content: string;
  /**
   * Path pattern within .claude/ directory (must start with '.claude/', no '..')
   */
  path_pattern: string;
  /**
   * Optional detailed description
   */
  description?: string | null;
  /**
   * Category for progressive disclosure (e.g., 'api', 'frontend', 'debugging')
   */
  category?: string | null;
  /**
   * Whether to auto-load when path pattern matches edited files
   */
  auto_load?: boolean;
  /**
   * Version identifier (semantic versioning recommended)
   */
  version?: string | null;
};
