/**
 * @skillmeat/backstage-plugin-scaffolder-backend
 *
 * Backstage scaffolder backend module providing custom actions
 * for SkillMeat (SAM) IDP integration.
 *
 * Actions:
 * - skillmeat:context:inject   - Injects Golden Context Pack files into the
 *                                 scaffolder workspace by calling the SAM scaffold API.
 * - skillmeat:deployment:register - Registers a completed deployment with SAM
 *                                    after publish:github writes the repo.
 *
 * Configuration (app-config.yaml):
 * ```yaml
 * skillmeat:
 *   baseUrl: https://sam.internal
 *   token: ${SAM_API_TOKEN}   # optional
 * ```
 *
 * Usage (packages/backend/src/index.ts):
 * ```typescript
 * import { createBackend } from '@backstage/backend-defaults';
 * import skillmeatScaffolderModule from '@skillmeat/backstage-plugin-scaffolder-backend';
 *
 * const backend = createBackend();
 * backend.add(skillmeatScaffolderModule);
 * await backend.start();
 * ```
 */

export type {
  ScaffoldRequest,
  ScaffoldResponse,
  RenderedFile,
  RegisterDeploymentRequest,
  RegisterDeploymentResponse,
  SkillMeatConfig,
} from './types';
