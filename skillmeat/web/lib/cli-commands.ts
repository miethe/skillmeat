/**
 * CLI Commands Utility
 *
 * Pure utility functions to generate SkillMeat CLI commands for deployment operations.
 * Used by the artifact modal and other UI components that need to display CLI commands.
 */

/**
 * Enum for CLI command types
 */
export enum CliCommandType {
  BASIC = 'basic',
  WITH_OVERWRITE = 'overwrite',
  WITH_PROJECT = 'project',
  WITH_PROFILE = 'profile',
  ALL_PROFILES = 'all_profiles',
}

/**
 * Options for generating deploy commands
 */
export interface DeployCommandOptions {
  /** Override existing artifact if deployed */
  overwrite?: boolean;
  /** Target project path for deployment */
  projectPath?: string;
  /** Deployment profile ID for profile-aware deployment */
  profileId?: string;
  /** Deploy to all configured profiles */
  allProfiles?: boolean;
}

/**
 * Generate a basic deploy command
 * @param artifactName - Name of the artifact to deploy
 * @returns CLI command string
 */
export function generateBasicDeployCommand(artifactName: string): string {
  return `skillmeat deploy ${artifactName.trim()}`;
}

/**
 * Generate a deploy command with overwrite flag
 * @param artifactName - Name of the artifact to deploy
 * @returns CLI command string with --overwrite flag
 */
export function generateDeployWithOverwriteCommand(artifactName: string): string {
  return `skillmeat deploy ${artifactName.trim()} --overwrite`;
}

/**
 * Generate a deploy command with project path
 * @param artifactName - Name of the artifact to deploy
 * @param projectPath - Target project directory (defaults to current directory)
 * @returns CLI command string with --project flag
 */
export function generateDeployWithProjectCommand(artifactName: string, projectPath = '.'): string {
  return `skillmeat deploy ${artifactName.trim()} --project ${projectPath}`;
}

/**
 * Generate a deploy command based on command type
 * @param artifactName - Name of the artifact to deploy
 * @param type - Type of command to generate
 * @param projectPath - Target project directory (used when type is WITH_PROJECT)
 * @returns CLI command string
 */
export function generateDeployCommand(
  artifactName: string,
  type: CliCommandType = CliCommandType.BASIC,
  projectPath = '.',
  profileId?: string
): string {
  const trimmedName = artifactName.trim();

  switch (type) {
    case CliCommandType.WITH_OVERWRITE:
      return generateDeployWithOverwriteCommand(trimmedName);
    case CliCommandType.WITH_PROJECT:
      return generateDeployWithProjectCommand(trimmedName, projectPath);
    case CliCommandType.WITH_PROFILE:
      return `skillmeat deploy ${trimmedName} --profile ${profileId || 'claude_code'}`;
    case CliCommandType.ALL_PROFILES:
      return `skillmeat deploy ${trimmedName} --all-profiles`;
    case CliCommandType.BASIC:
    default:
      return generateBasicDeployCommand(trimmedName);
  }
}

/**
 * Generate a deploy command with full options
 * @param artifactName - Name of the artifact to deploy
 * @param options - Command options
 * @returns CLI command string with applicable flags
 */
export function generateDeployCommandWithOptions(
  artifactName: string,
  options: DeployCommandOptions = {}
): string {
  const trimmedName = artifactName.trim();
  const parts = ['skillmeat deploy', trimmedName];

  if (options.overwrite) {
    parts.push('--overwrite');
  }

  if (options.projectPath && options.projectPath !== '.') {
    parts.push('--project', options.projectPath);
  }

  if (options.allProfiles) {
    parts.push('--all-profiles');
  } else if (options.profileId) {
    parts.push('--profile', options.profileId);
  }

  return parts.join(' ');
}
