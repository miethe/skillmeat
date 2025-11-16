/**
 * Bundle Types for SkillMeat Sharing
 *
 * Types for exporting, importing, and sharing artifact bundles
 */

import type { Artifact } from "./artifact";

export type BundleFormat = "zip" | "tar.gz";
export type CompressionLevel = "none" | "fast" | "balanced" | "best";
export type ConflictStrategy = "merge" | "fork" | "skip" | "overwrite";
export type PermissionLevel = "viewer" | "importer" | "publisher" | "admin";
export type VaultProvider = "local" | "github" | "s3" | "gdrive";

export interface BundleMetadata {
  name: string;
  description?: string;
  tags?: string[];
  license?: string;
  author?: string;
  version?: string;
  createdAt: string;
  updatedAt?: string;
}

export interface ExportOptions {
  includeDependencies: boolean;
  compressionLevel: CompressionLevel;
  format: BundleFormat;
  vault?: VaultConfig;
  generateShareLink: boolean;
  linkExpiration?: number; // hours, 0 = no expiration
  permissionLevel: PermissionLevel;
}

export interface VaultConfig {
  provider: VaultProvider;
  path?: string;
  credentials?: Record<string, unknown>;
}

export interface ImportOptions {
  conflictStrategy: ConflictStrategy;
  skipValidation: boolean;
  dryRun: boolean;
}

export interface BundleArtifact {
  artifact: Artifact;
  dependencies?: string[]; // artifact IDs
  files?: string[]; // file paths within bundle
}

export interface Bundle {
  id: string;
  metadata: BundleMetadata;
  artifacts: BundleArtifact[];
  exportedAt: string;
  exportedBy: string;
  format: BundleFormat;
  size: number; // bytes
  checksumSha256: string;
  shareLink?: ShareLink;
  vault?: VaultConfig;
}

export interface ShareLink {
  url: string;
  shortUrl?: string;
  qrCode?: string; // base64 encoded QR code image
  expiresAt?: string;
  permissionLevel: PermissionLevel;
  downloadCount: number;
  createdAt: string;
}

export interface BundlePreview {
  bundle: Bundle;
  conflicts: ConflictInfo[];
  newArtifacts: string[]; // artifact IDs
  existingArtifacts: string[]; // artifact IDs
  willImport: number;
  willSkip: number;
  willMerge: number;
  willFork: number;
}

export interface ConflictInfo {
  artifactId: string;
  artifactName: string;
  existingVersion: string;
  incomingVersion: string;
  conflictType: "version" | "content" | "metadata";
  suggestedStrategy: ConflictStrategy;
}

export interface ImportResult {
  success: boolean;
  imported: string[]; // artifact IDs
  skipped: string[]; // artifact IDs
  merged: string[]; // artifact IDs
  forked: string[]; // artifact IDs
  errors: ImportError[];
  summary: string;
}

export interface ImportError {
  artifactId: string;
  artifactName: string;
  error: string;
  severity: "warning" | "error";
}

export interface ExportRequest {
  artifactIds: string[];
  metadata: BundleMetadata;
  options: ExportOptions;
}

export interface ImportRequest {
  source: BundleSource;
  options: ImportOptions;
}

export type BundleSource =
  | { type: "file"; file: File }
  | { type: "url"; url: string }
  | { type: "vault"; vault: VaultConfig; path: string };

export interface BundleListItem {
  id: string;
  metadata: BundleMetadata;
  artifactCount: number;
  size: number;
  format: BundleFormat;
  exportedAt: string;
  shareLink?: ShareLink;
  downloadCount: number;
  isImported: boolean; // true if this was imported from elsewhere
}

export interface BundleAnalytics {
  bundleId: string;
  downloads: number;
  uniqueDownloaders: number;
  lastDownloaded?: string;
  popularArtifacts: Array<{
    artifactId: string;
    artifactName: string;
    downloads: number;
  }>;
}

export interface UserPermission {
  userId: string;
  userName: string;
  level: PermissionLevel;
  grantedAt: string;
  grantedBy: string;
}

export interface BundlePermissions {
  bundleId: string;
  owner: string;
  isPublic: boolean;
  users: UserPermission[];
  defaultPermission: PermissionLevel;
}
