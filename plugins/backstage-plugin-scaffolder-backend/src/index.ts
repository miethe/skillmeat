/**
 * @skillmeat/backstage-plugin-scaffolder-backend
 *
 * Backstage scaffolder backend module providing custom actions
 * for SkillMeat (SAM) IDP integration.
 *
 * Actions:
 * - skillmeat:context:inject        - Injects Golden Context Pack files into the
 *                                     scaffolder workspace via the SAM scaffold API.
 * - skillmeat:deployment:register   - Registers a completed deployment with SAM
 *                                     after publish:github writes the repo.
 * - skillmeat:attest                - Creates attestation records for one or more
 *                                     artifacts via the SAM attestations API.
 * - skillmeat:bom:generate          - Triggers on-demand BOM generation via the
 *                                     SAM BOM API and returns snapshot metadata.
 *
 * Configuration (app-config.yaml):
 * ```yaml
 * skillmeat:
 *   baseUrl: https://sam.internal
 *   token: ${SAM_API_TOKEN}   # optional
 * ```
 *
 * Usage — new backend system (packages/backend/src/index.ts):
 * ```typescript
 * import { createBackend } from '@backstage/backend-defaults';
 * import { skillmeatScaffolderModule } from '@skillmeat/backstage-plugin-scaffolder-backend';
 *
 * const backend = createBackend();
 * backend.add(import('@backstage/plugin-scaffolder-backend/alpha'));
 * backend.add(skillmeatScaffolderModule);
 * await backend.start();
 * ```
 */

import { createBackendModule } from '@backstage/backend-plugin-api';
import { scaffolderActionsExtensionPoint } from '@backstage/plugin-scaffolder-node/alpha';
import { createSkillMeatInjectAction } from './actions/inject';
import { createSkillMeatRegisterAction } from './actions/register';
import { createSkillMeatAttestAction } from './actions/attest';
import { createSkillmeatBomGenerateAction } from './actions/bom-generate';

/**
 * Backstage backend module that registers SkillMeat scaffolder actions with
 * the scaffolder plugin via the extension point mechanism.
 *
 * Install via the new backend system:
 * ```typescript
 * backend.add(skillmeatScaffolderModule);
 * ```
 *
 * @public
 */
export const skillmeatScaffolderModule = createBackendModule({
  pluginId: 'scaffolder',
  moduleId: 'skillmeat',
  register(env) {
    env.registerInit({
      deps: {
        scaffolder: scaffolderActionsExtensionPoint,
      },
      async init({ scaffolder }) {
        scaffolder.addActions(
          createSkillMeatInjectAction(),
          createSkillMeatRegisterAction(),
          createSkillMeatAttestAction(),
          createSkillmeatBomGenerateAction(),
        );
      },
    });
  },
});

// Re-export action factories for consumers using the legacy backend system
// or manual action registration.
export {
  createSkillMeatInjectAction,
  createSkillMeatRegisterAction,
  createSkillMeatAttestAction,
  createSkillmeatBomGenerateAction,
};

// Re-export all public types so consumers don't need a direct dependency on
// this package's internal modules.
export type {
  ScaffoldRequest,
  ScaffoldResponse,
  RenderedFile,
  RegisterDeploymentRequest,
  RegisterDeploymentResponse,
  AttestationRequest,
  AttestationResponse,
  BomGenerateRequest,
  BomGenerateResponse,
  SkillMeatConfig,
} from './types';

// SkillBOMCard — Backstage EntityPage card scaffold component.
// Full Backstage frontend integration is tracked as a follow-on task.
export { SkillBOMCard } from './components/SkillBOMCard';
export type {
  SkillBOMCardProps,
  BomCardResponse,
  BomCardArtifactEntry,
} from './components/SkillBOMCard';

// Default export for convenience — matches the import pattern used by
// Backstage's new backend system dynamic plugin loader.
export default skillmeatScaffolderModule;
