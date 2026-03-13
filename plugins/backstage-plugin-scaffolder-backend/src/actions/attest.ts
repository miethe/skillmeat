/**
 * skillmeat:attest — Backstage scaffolder action
 *
 * Creates attestation records for one or more artifacts by calling
 * POST /api/v1/attestations on the SkillMeat API.  Designed for use in
 * Backstage software templates that require artifact sign-off as part of
 * deployment or release workflows.
 *
 * Partial success is tolerated: attestations that succeed are collected and
 * returned even if others fail.  Failures are logged as warnings rather than
 * thrown so a single bad artifact_id does not abort the entire template step.
 *
 * Config resolution order (first wins):
 *   1. ctx.input.apiBaseUrl / ctx.input.apiKey (per-step overrides in the template)
 *   2. Backstage app-config.yaml → skillmeat.baseUrl / skillmeat.token
 */

import { createTemplateAction } from '@backstage/plugin-scaffolder-node';
import fetch from 'node-fetch';
import { AttestationRequest, AttestationResponse } from '../types';

export function createSkillMeatAttestAction() {
  return createTemplateAction<{
    artifactIds: string[];
    ownerScope: 'user' | 'team' | 'enterprise';
    notes?: string;
    apiBaseUrl?: string;
    apiKey?: string;
  }>({
    id: 'skillmeat:attest',
    description:
      'Creates SkillMeat attestation records for one or more artifacts',

    schema: {
      input: {
        type: 'object',
        required: ['artifactIds', 'ownerScope'],
        properties: {
          artifactIds: {
            type: 'array',
            items: { type: 'string' },
            title: 'Artifact IDs',
            description:
              "List of artifact identifiers to attest, in 'type:name' format (e.g. ['skill:canvas-design'])",
          },
          ownerScope: {
            type: 'string',
            enum: ['user', 'team', 'enterprise'],
            title: 'Owner Scope',
            description:
              "Ownership scope for the attestations: 'user', 'team', or 'enterprise'",
          },
          notes: {
            type: 'string',
            title: 'Notes',
            description:
              'Optional free-text compliance notes stored with each attestation',
          },
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
        },
      },
      output: {
        type: 'object',
        properties: {
          attestationIds: {
            type: 'array',
            items: { type: 'string' },
            title: 'Attestation IDs',
            description: 'UUIDs of the successfully created attestation records',
          },
          count: {
            type: 'number',
            title: 'Count',
            description: 'Number of attestations successfully created',
          },
        },
      },
    },

    async handler(ctx) {
      const {
        artifactIds,
        ownerScope,
        notes,
        apiBaseUrl: inputBaseUrl,
        apiKey: inputApiKey,
      } = ctx.input;

      // Resolve SAM API connection details: per-step inputs take precedence over
      // global Backstage config.  Same resolution pattern as other SkillMeat actions.
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

      const url = `${baseUrl.replace(/\/$/, '')}/api/v1/attestations`;

      ctx.logger.info(
        `skillmeat:attest — attesting ${artifactIds.length} artifact(s) at ${url} with owner_scope '${ownerScope}'`,
      );

      const attestationIds: string[] = [];

      // Attest each artifact individually.  Partial success is intentional:
      // a missing artifact_id should not block attestation of others.
      for (const artifactId of artifactIds) {
        const requestBody: AttestationRequest = {
          artifact_id: artifactId,
          owner_scope: ownerScope,
          ...(notes !== undefined && { notes }),
        };

        ctx.logger.info(`Attesting artifact '${artifactId}'`);

        let response;
        try {
          response = await fetch(url, {
            method: 'POST',
            headers,
            body: JSON.stringify(requestBody),
          });
        } catch (networkErr) {
          // Network-level failure — log and continue rather than aborting.
          ctx.logger.warn(
            `Network error attesting artifact '${artifactId}': ${(networkErr as Error).message}`,
          );
          continue;
        }

        if (!response.ok) {
          // Surface the response body so template authors can diagnose failures
          // without needing direct access to SkillMeat server logs.
          const errorBody = await response
            .text()
            .catch(() => '<unreadable body>');
          ctx.logger.warn(
            `SkillMeat attestation API returned ${response.status} ${response.statusText} ` +
              `for artifact '${artifactId}': ${errorBody}`,
          );
          continue;
        }

        const data = (await response.json()) as AttestationResponse;
        attestationIds.push(data.id);

        ctx.logger.info(
          `Attestation created — id: '${data.id}', artifact: '${artifactId}'`,
        );
      }

      ctx.logger.info(
        `skillmeat:attest complete — created ${attestationIds.length}/${artifactIds.length} attestation(s)`,
      );

      ctx.output('attestationIds', attestationIds);
      ctx.output('count', attestationIds.length);
    },
  });
}
