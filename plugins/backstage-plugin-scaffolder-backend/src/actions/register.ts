/**
 * skillmeat:deployment:register — Backstage scaffolder action
 *
 * Calls POST /api/v1/integrations/idp/register-deployment on the SAM API
 * after publish:github completes, associating the new repository with the
 * SAM artifact that was used as the scaffold source.
 *
 * Config resolution order (first wins):
 *   1. ctx.input.baseUrl / ctx.input.token (per-step overrides in the template)
 *   2. Backstage app-config.yaml → skillmeat.baseUrl / skillmeat.token
 *
 * This action is blocking — downstream steps receive deploymentSetId and
 * created flag immediately, enabling conditional logic in the template.
 */

import { createTemplateAction } from '@backstage/plugin-scaffolder-node';
import { RootConfigService } from '@backstage/backend-plugin-api';
import fetch from 'node-fetch';
import { RegisterDeploymentRequest, RegisterDeploymentResponse } from '../types';

export function createSkillMeatRegisterAction({ config }: { config: RootConfigService }) {
  return createTemplateAction<{
    repoUrl: string;
    targetId: string;
    metadata?: Record<string, string>;
    baseUrl?: string;
    token?: string;
  }>({
    id: 'skillmeat:deployment:register',
    description: 'Registers a SkillMeat deployment after project scaffolding',

    schema: {
      input: {
        type: 'object',
        required: ['repoUrl', 'targetId'],
        properties: {
          repoUrl: {
            type: 'string',
            title: 'Repository URL',
            description:
              'HTTPS URL of the newly created repository (typically from publish:github output)',
          },
          targetId: {
            type: 'string',
            title: 'Target ID',
            description:
              'SAM artifact identifier in type:name format (e.g. composite:fin-serv-compliance)',
          },
          metadata: {
            type: 'object',
            title: 'Deployment Metadata',
            description:
              'Optional key/value metadata stored with the deployment record',
            additionalProperties: { type: 'string' },
          },
          baseUrl: {
            type: 'string',
            title: 'SAM API Base URL',
            description: 'Override the configured SAM API URL',
          },
          token: {
            type: 'string',
            title: 'SAM API Token',
            description: 'Override the configured SAM API bearer token',
          },
        },
      },
      output: {
        type: 'object',
        properties: {
          deploymentSetId: {
            type: 'string',
            title: 'Deployment Set ID',
            description:
              'UUID of the created or updated DeploymentSet record',
          },
          created: {
            type: 'boolean',
            title: 'Created',
            description:
              'True if a new deployment was created, false if existing was updated',
          },
        },
      },
    },

    async handler(ctx) {
      const {
        repoUrl,
        targetId,
        metadata = {},
        baseUrl: inputBaseUrl,
        token: inputToken,
      } = ctx.input;

      // Resolve SAM API connection details: per-step inputs take precedence over
      // global Backstage config.  Same pattern as skillmeat:context:inject.
      const baseUrl =
        inputBaseUrl ??
        config.getOptionalString('skillmeat.baseUrl') ??
        '';

      if (!baseUrl) {
        throw new Error(
          'SAM API baseUrl is required. Provide it via the action input `baseUrl` ' +
            'or via `skillmeat.baseUrl` in app-config.yaml.',
        );
      }

      const token =
        inputToken ??
        config.getOptionalString('skillmeat.token') ??
        undefined;

      // Build request headers.  Authorization header is omitted entirely when
      // no token is configured, supporting unauthenticated internal deployments.
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const url = `${baseUrl.replace(/\/$/, '')}/api/v1/integrations/idp/register-deployment`;

      const requestBody: RegisterDeploymentRequest = {
        repo_url: repoUrl,
        target_id: targetId,
        metadata,
      };

      ctx.logger.info(
        `Registering deployment — repo: '${repoUrl}', target: '${targetId}' at ${url}`,
      );

      const response = await fetch(url, {
        method: 'POST',
        headers,
        body: JSON.stringify(requestBody),
      });

      if (!response.ok) {
        // Surface the response body so template authors can diagnose failures
        // without needing direct access to SAM server logs.
        const errorBody = await response.text().catch(() => '<unreadable body>');
        throw new Error(
          `SAM register-deployment API returned ${response.status} ${response.statusText}: ${errorBody}`,
        );
      }

      const data = (await response.json()) as RegisterDeploymentResponse;

      const verb = data.created ? 'Created' : 'Updated';
      ctx.logger.info(
        `${verb} deployment set '${data.deployment_set_id}' for repo '${repoUrl}'`,
      );

      ctx.output('deploymentSetId', data.deployment_set_id);
      ctx.output('created', data.created);
    },
  });
}
