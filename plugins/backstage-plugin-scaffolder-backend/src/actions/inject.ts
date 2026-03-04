/**
 * skillmeat:context:inject — Backstage scaffolder action
 *
 * Calls POST /api/v1/integrations/idp/scaffold on the SAM API and writes
 * the returned base64-encoded files into the Backstage scaffolder workspace.
 *
 * Config resolution order (first wins):
 *   1. ctx.input.baseUrl / ctx.input.token (per-step overrides in the template)
 *   2. Backstage app-config.yaml → skillmeat.baseUrl / skillmeat.token
 */

import { createTemplateAction } from '@backstage/plugin-scaffolder-node';
import fetch from 'node-fetch';
import { ScaffoldRequest, ScaffoldResponse } from '../types';

export function createSkillMeatInjectAction() {
  return createTemplateAction<{
    targetId: string;
    variables?: Record<string, string>;
    baseUrl?: string;
    token?: string;
  }>({
    id: 'skillmeat:context:inject',
    description:
      'Injects a SkillMeat Golden Context Pack into the scaffolder workspace',

    schema: {
      input: {
        type: 'object',
        required: ['targetId'],
        properties: {
          targetId: {
            type: 'string',
            title: 'Target ID',
            description:
              'SAM artifact identifier in type:name format (e.g. composite:fin-serv-compliance)',
          },
          variables: {
            type: 'object',
            title: 'Template Variables',
            description:
              'Key/value pairs for template variable substitution',
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
          filesWritten: {
            type: 'number',
            title: 'Files Written',
            description: 'Number of files written to the workspace',
          },
        },
      },
    },

    async handler(ctx) {
      const { targetId, variables = {}, baseUrl: inputBaseUrl, token: inputToken } =
        ctx.input;

      // Resolve SAM API connection details: per-step inputs take precedence over
      // global Backstage config.  We intentionally keep this simple — no deep
      // config validation — so the plugin stays self-contained for environments
      // that prefer template-level configuration over app-config.yaml.
      const baseUrl =
        inputBaseUrl ??
        ctx.config?.getOptionalString('skillmeat.baseUrl') ??
        '';

      if (!baseUrl) {
        throw new Error(
          'SAM API baseUrl is required. Provide it via the action input `baseUrl` ' +
            'or via `skillmeat.baseUrl` in app-config.yaml.',
        );
      }

      const token =
        inputToken ??
        ctx.config?.getOptionalString('skillmeat.token') ??
        undefined;

      // Build request headers.  The Authorization header is omitted entirely
      // when no token is configured, supporting unauthenticated internal deployments.
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const url = `${baseUrl.replace(/\/$/, '')}/api/v1/integrations/idp/scaffold`;

      const requestBody: ScaffoldRequest = {
        target_id: targetId,
        variables,
      };

      ctx.logger.info(
        `Calling SAM scaffold API for target '${targetId}' at ${url}`,
      );

      const response = await fetch(url, {
        method: 'POST',
        headers,
        body: JSON.stringify(requestBody),
      });

      if (!response.ok) {
        // Surface the response body in the error message so template authors can
        // diagnose problems without needing to inspect SAM server logs directly.
        const errorBody = await response.text().catch(() => '<unreadable body>');
        throw new Error(
          `SAM scaffold API returned ${response.status} ${response.statusText}: ${errorBody}`,
        );
      }

      const data = (await response.json()) as ScaffoldResponse;
      const files = data.files ?? [];

      if (files.length === 0) {
        ctx.logger.warn(
          `SAM scaffold API returned 0 files for target '${targetId}'. ` +
            'Verify the target_id is correct and the target contains renderable files.',
        );
        ctx.output('filesWritten', 0);
        return;
      }

      // Write each file into the scaffolder workspace.  Paths from SAM are relative
      // (e.g. `.claude/CLAUDE.md`) — ctx.createFile() places them relative to the
      // workspace root, which matches the expected layout.
      for (const file of files) {
        const content = Buffer.from(file.content_base64, 'base64').toString('utf-8');
        ctx.logger.info(`Writing file: ${file.path}`);
        await ctx.createFile({ path: file.path, content });
      }

      ctx.logger.info(
        `skillmeat:context:inject complete — wrote ${files.length} file(s) for target '${targetId}'`,
      );

      ctx.output('filesWritten', files.length);
    },
  });
}
