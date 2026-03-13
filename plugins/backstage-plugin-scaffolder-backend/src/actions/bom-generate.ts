/**
 * skillmeat:bom:generate — Backstage scaffolder action
 *
 * Triggers an on-demand Bill of Materials generation by calling
 * POST /api/v1/bom/generate on the SkillMeat API.  The BOM snapshot is
 * persisted server-side and can optionally be signed with an Ed25519 key.
 *
 * Config resolution order (first wins):
 *   1. ctx.input.apiBaseUrl / ctx.input.apiKey (per-step overrides in the template)
 *   2. Backstage app-config.yaml → skillmeat.baseUrl / skillmeat.token
 */

import { createTemplateAction } from '@backstage/plugin-scaffolder-node';
import fetch from 'node-fetch';
import { BomGenerateRequest, BomGenerateResponse } from '../types';

export function createSkillmeatBomGenerateAction() {
  return createTemplateAction<{
    apiBaseUrl?: string;
    apiKey?: string;
    projectPath?: string;
    sign?: boolean;
  }>({
    id: 'skillmeat:bom:generate',
    description:
      'Triggers BOM generation via the SkillMeat API and returns the snapshot metadata',

    schema: {
      input: {
        type: 'object',
        properties: {
          apiBaseUrl: {
            type: 'string',
            title: 'SkillMeat API Base URL',
            description: 'Override the configured SkillMeat API URL',
          },
          apiKey: {
            type: 'string',
            title: 'SkillMeat API Key',
            description:
              'Override the configured SkillMeat enterprise PAT for authentication',
          },
          projectPath: {
            type: 'string',
            title: 'Project Path',
            description:
              'Project scope to filter artifacts for the BOM. When omitted, generates a collection-level BOM.',
          },
          sign: {
            type: 'boolean',
            title: 'Sign BOM',
            description:
              'Sign the generated BOM with the local Ed25519 signing key (default: false)',
          },
        },
      },
      output: {
        type: 'object',
        properties: {
          snapshotId: {
            type: 'string',
            title: 'Snapshot ID',
            description: 'Primary key of the generated BOM snapshot',
          },
          artifactCount: {
            type: 'number',
            title: 'Artifact Count',
            description: 'Number of artifacts included in the BOM',
          },
          generatedAt: {
            type: 'string',
            title: 'Generated At',
            description: 'ISO-8601 UTC timestamp of BOM generation',
          },
        },
      },
    },

    async handler(ctx) {
      const {
        apiBaseUrl: inputBaseUrl,
        apiKey: inputApiKey,
        projectPath,
        sign = false,
      } = ctx.input;

      // Resolve SkillMeat API connection details: per-step inputs take precedence
      // over global Backstage config.  Same resolution pattern as other SkillMeat actions.
      const baseUrl =
        inputBaseUrl ??
        ctx.config?.getOptionalString('skillmeat.baseUrl') ??
        '';

      if (!baseUrl) {
        throw new Error(
          'SkillMeat API baseUrl is required. Provide it via the action input `apiBaseUrl` ' +
            'or via `skillmeat.baseUrl` in app-config.yaml.',
        );
      }

      const apiKey =
        inputApiKey ??
        ctx.config?.getOptionalString('skillmeat.token') ??
        undefined;

      // Build request headers.  The Authorization header is omitted entirely
      // when no API key is configured, supporting unauthenticated internal deployments.
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      };
      if (apiKey) {
        headers['Authorization'] = `Bearer ${apiKey}`;
      }

      const url = `${baseUrl.replace(/\/$/, '')}/api/v1/bom/generate`;

      const requestBody: BomGenerateRequest = {
        ...(projectPath !== undefined && { project_id: projectPath }),
        auto_sign: sign,
      };

      ctx.logger.info(
        `skillmeat:bom:generate — triggering BOM generation at ${url}` +
          (projectPath ? ` for project '${projectPath}'` : ' (collection-level)') +
          (sign ? ' with auto-sign' : ''),
      );

      const response = await fetch(url, {
        method: 'POST',
        headers,
        body: JSON.stringify(requestBody),
      });

      if (!response.ok) {
        // Surface the response body so template authors can diagnose failures
        // without needing direct access to SkillMeat server logs.
        const errorBody = await response.text().catch(() => '<unreadable body>');
        throw new Error(
          `SkillMeat BOM generate API returned ${response.status} ${response.statusText}: ${errorBody}`,
        );
      }

      const data = (await response.json()) as BomGenerateResponse;

      ctx.logger.info(
        `skillmeat:bom:generate complete — snapshot id: ${data.id}, ` +
          `artifact count: ${data.bom.artifact_count}, signed: ${data.signed}`,
      );

      ctx.output('snapshotId', String(data.id));
      ctx.output('artifactCount', data.bom.artifact_count);
      ctx.output('generatedAt', data.created_at);
    },
  });
}
