/**
 * Tests for SkillMeat Backstage scaffolder actions.
 *
 * Covers:
 * - skillmeat:attest — happy path, partial success, API error, missing baseUrl
 * - skillmeat:bom:generate — happy path, signed BOM, API error, missing baseUrl
 *
 * Fetch is mocked at the module level so no real HTTP calls are made.
 */

import { createSkillMeatAttestAction } from '../actions/attest';
import { createSkillmeatBomGenerateAction } from '../actions/bom-generate';

// ---------------------------------------------------------------------------
// fetch mock — replaces node-fetch module-wide
// ---------------------------------------------------------------------------

const mockFetch = jest.fn();

jest.mock('node-fetch', () => ({
  __esModule: true,
  default: (...args: unknown[]) => mockFetch(...args),
}));

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Build a minimal mock HandlerContext compatible with the actions under test. */
function makeCtx(inputOverrides: Record<string, unknown> = {}) {
  const outputs: Record<string, unknown> = {};
  return {
    input: inputOverrides,
    output: jest.fn((key: string, value: unknown) => {
      outputs[key] = value;
    }),
    logger: {
      info: jest.fn(),
      warn: jest.fn(),
      error: jest.fn(),
      debug: jest.fn(),
    },
    config: {
      getOptionalString: jest.fn((_key: string) => undefined),
    },
    _outputs: outputs,
  };
}

/** Build a mock fetch response. */
function mockResponse(
  body: unknown,
  status = 200,
  ok = true,
): ReturnType<typeof jest.fn> {
  return {
    ok,
    status,
    statusText: ok ? 'OK' : 'Internal Server Error',
    json: jest.fn().mockResolvedValue(body),
    text: jest.fn().mockResolvedValue(JSON.stringify(body)),
  } as unknown as ReturnType<typeof jest.fn>;
}

// ---------------------------------------------------------------------------
// skillmeat:attest tests
// ---------------------------------------------------------------------------

describe('createSkillMeatAttestAction', () => {
  let action: ReturnType<typeof createSkillMeatAttestAction>;

  beforeEach(() => {
    action = createSkillMeatAttestAction();
    mockFetch.mockReset();
  });

  it('has the correct action id', () => {
    expect(action.id).toBe('skillmeat:attest');
  });

  describe('happy path — single artifact', () => {
    it('calls POST /api/v1/attestations and outputs attestationIds and count', async () => {
      const attestationResp = {
        id: 'aaaa-bbbb-cccc',
        artifact_id: 'skill:canvas-design',
        owner_type: 'user',
        owner_id: 'user-1',
        roles: [],
        scopes: [],
        visibility: 'private',
        created_at: '2026-03-13T10:00:00Z',
      };
      mockFetch.mockResolvedValueOnce(mockResponse(attestationResp, 200, true));

      const ctx = makeCtx({
        artifactIds: ['skill:canvas-design'],
        ownerScope: 'user',
        apiBaseUrl: 'http://skillmeat.test',
      });

      await action.handler(ctx as unknown as Parameters<typeof action.handler>[0]);

      expect(mockFetch).toHaveBeenCalledTimes(1);
      const [url, opts] = mockFetch.mock.calls[0];
      expect(url).toBe('http://skillmeat.test/api/v1/attestations');
      expect(opts.method).toBe('POST');

      const body = JSON.parse(opts.body as string);
      expect(body.artifact_id).toBe('skill:canvas-design');
      expect(body.owner_scope).toBe('user');

      expect(ctx._outputs.attestationIds).toEqual(['aaaa-bbbb-cccc']);
      expect(ctx._outputs.count).toBe(1);
    });

    it('includes Authorization header when apiKey is provided', async () => {
      mockFetch.mockResolvedValueOnce(
        mockResponse({ id: 'id-1', artifact_id: 'skill:x', owner_type: 'user', owner_id: 'u', roles: [], scopes: [], visibility: 'private' }),
      );

      const ctx = makeCtx({
        artifactIds: ['skill:x'],
        ownerScope: 'user',
        apiBaseUrl: 'http://sam.internal',
        apiKey: 'pat-secret',
      });

      await action.handler(ctx as unknown as Parameters<typeof action.handler>[0]);

      const [, opts] = mockFetch.mock.calls[0];
      expect((opts.headers as Record<string, string>)['Authorization']).toBe(
        'Bearer pat-secret',
      );
    });

    it('omits Authorization header when no apiKey is configured', async () => {
      mockFetch.mockResolvedValueOnce(
        mockResponse({ id: 'id-2', artifact_id: 'skill:y', owner_type: 'user', owner_id: 'u', roles: [], scopes: [], visibility: 'private' }),
      );

      const ctx = makeCtx({
        artifactIds: ['skill:y'],
        ownerScope: 'user',
        apiBaseUrl: 'http://sam.internal',
      });

      await action.handler(ctx as unknown as Parameters<typeof action.handler>[0]);

      const [, opts] = mockFetch.mock.calls[0];
      expect(
        (opts.headers as Record<string, string>)['Authorization'],
      ).toBeUndefined();
    });

    it('includes optional notes in the request body when provided', async () => {
      mockFetch.mockResolvedValueOnce(
        mockResponse({ id: 'id-3', artifact_id: 'skill:z', owner_type: 'user', owner_id: 'u', roles: [], scopes: [], visibility: 'private' }),
      );

      const ctx = makeCtx({
        artifactIds: ['skill:z'],
        ownerScope: 'enterprise',
        notes: 'Approved for prod',
        apiBaseUrl: 'http://sam.internal',
      });

      await action.handler(ctx as unknown as Parameters<typeof action.handler>[0]);

      const [, opts] = mockFetch.mock.calls[0];
      const body = JSON.parse(opts.body as string);
      expect(body.notes).toBe('Approved for prod');
    });
  });

  describe('partial success — multiple artifacts', () => {
    it('returns only successfully attested artifact ids when one fails', async () => {
      const goodResp = {
        id: 'good-id',
        artifact_id: 'skill:good',
        owner_type: 'user',
        owner_id: 'u',
        roles: [],
        scopes: [],
        visibility: 'private',
      };

      // First call succeeds, second returns 500
      mockFetch
        .mockResolvedValueOnce(mockResponse(goodResp, 200, true))
        .mockResolvedValueOnce(mockResponse({ detail: 'not found' }, 500, false));

      const ctx = makeCtx({
        artifactIds: ['skill:good', 'skill:bad'],
        ownerScope: 'user',
        apiBaseUrl: 'http://sam.internal',
      });

      await action.handler(ctx as unknown as Parameters<typeof action.handler>[0]);

      expect(ctx._outputs.attestationIds).toEqual(['good-id']);
      expect(ctx._outputs.count).toBe(1);
      // Failure should be logged as a warning, not thrown
      expect(ctx.logger.warn).toHaveBeenCalled();
    });

    it('returns empty list when all artifacts fail', async () => {
      mockFetch
        .mockResolvedValueOnce(mockResponse({ detail: 'error' }, 500, false))
        .mockResolvedValueOnce(mockResponse({ detail: 'error' }, 404, false));

      const ctx = makeCtx({
        artifactIds: ['skill:a', 'skill:b'],
        ownerScope: 'user',
        apiBaseUrl: 'http://sam.internal',
      });

      await action.handler(ctx as unknown as Parameters<typeof action.handler>[0]);

      expect(ctx._outputs.attestationIds).toEqual([]);
      expect(ctx._outputs.count).toBe(0);
    });

    it('continues after a network-level error on one artifact', async () => {
      const goodResp = {
        id: 'net-good-id',
        artifact_id: 'skill:ok',
        owner_type: 'user',
        owner_id: 'u',
        roles: [],
        scopes: [],
        visibility: 'private',
      };

      mockFetch
        .mockRejectedValueOnce(new Error('ECONNREFUSED'))
        .mockResolvedValueOnce(mockResponse(goodResp, 200, true));

      const ctx = makeCtx({
        artifactIds: ['skill:unreachable', 'skill:ok'],
        ownerScope: 'user',
        apiBaseUrl: 'http://sam.internal',
      });

      await action.handler(ctx as unknown as Parameters<typeof action.handler>[0]);

      expect(ctx._outputs.count).toBe(1);
      expect(ctx._outputs.attestationIds).toEqual(['net-good-id']);
      expect(ctx.logger.warn).toHaveBeenCalledWith(
        expect.stringContaining('Network error'),
      );
    });
  });

  describe('error handling', () => {
    it('throws when apiBaseUrl is missing and config has no skillmeat.baseUrl', async () => {
      const ctx = makeCtx({
        artifactIds: ['skill:x'],
        ownerScope: 'user',
        // no apiBaseUrl, config returns undefined
      });

      await expect(
        action.handler(ctx as unknown as Parameters<typeof action.handler>[0]),
      ).rejects.toThrow('baseUrl is required');
    });

    it('uses skillmeat.baseUrl from config when apiBaseUrl input is absent', async () => {
      mockFetch.mockResolvedValueOnce(
        mockResponse({ id: 'cfg-id', artifact_id: 'skill:x', owner_type: 'user', owner_id: 'u', roles: [], scopes: [], visibility: 'private' }),
      );

      const ctx = makeCtx({
        artifactIds: ['skill:x'],
        ownerScope: 'user',
      });
      // Override config to return a baseUrl
      ctx.config.getOptionalString = jest.fn((key: string) =>
        key === 'skillmeat.baseUrl' ? 'http://config-url.test' : undefined,
      );

      await action.handler(ctx as unknown as Parameters<typeof action.handler>[0]);

      const [url] = mockFetch.mock.calls[0];
      expect(url).toBe('http://config-url.test/api/v1/attestations');
    });
  });
});

// ---------------------------------------------------------------------------
// skillmeat:bom:generate tests
// ---------------------------------------------------------------------------

describe('createSkillmeatBomGenerateAction', () => {
  let action: ReturnType<typeof createSkillmeatBomGenerateAction>;

  beforeEach(() => {
    action = createSkillmeatBomGenerateAction();
    mockFetch.mockReset();
  });

  it('has the correct action id', () => {
    expect(action.id).toBe('skillmeat:bom:generate');
  });

  describe('happy path — collection-level BOM', () => {
    it('calls POST /api/v1/bom/generate and outputs snapshotId, artifactCount, generatedAt', async () => {
      const bomResp = {
        id: 42,
        project_id: null,
        owner_type: 'user',
        created_at: '2026-03-13T10:00:00Z',
        bom: {
          schema_version: '1.0.0',
          generated_at: '2026-03-13T10:00:00Z',
          artifact_count: 7,
          artifacts: [],
        },
        signed: false,
      };
      mockFetch.mockResolvedValueOnce(mockResponse(bomResp, 201, true));

      const ctx = makeCtx({
        apiBaseUrl: 'http://skillmeat.test',
      });

      await action.handler(ctx as unknown as Parameters<typeof action.handler>[0]);

      expect(mockFetch).toHaveBeenCalledTimes(1);
      const [url, opts] = mockFetch.mock.calls[0];
      expect(url).toBe('http://skillmeat.test/api/v1/bom/generate');
      expect(opts.method).toBe('POST');

      const body = JSON.parse(opts.body as string);
      expect(body.auto_sign).toBe(false);
      expect(body.project_id).toBeUndefined();

      expect(ctx._outputs.snapshotId).toBe('42');
      expect(ctx._outputs.artifactCount).toBe(7);
      expect(ctx._outputs.generatedAt).toBe('2026-03-13T10:00:00Z');
    });
  });

  describe('happy path — project-scoped BOM with signing', () => {
    it('sends project_id and auto_sign=true when sign=true and projectPath is set', async () => {
      const bomResp = {
        id: 99,
        project_id: '/home/user/myproject',
        owner_type: 'user',
        created_at: '2026-03-13T11:00:00Z',
        bom: {
          schema_version: '1.0.0',
          generated_at: '2026-03-13T11:00:00Z',
          artifact_count: 3,
          artifacts: [],
        },
        signed: true,
        signature: 'deadbeef',
        signing_key_id: 'key-fingerprint',
      };
      mockFetch.mockResolvedValueOnce(mockResponse(bomResp, 201, true));

      const ctx = makeCtx({
        apiBaseUrl: 'http://skillmeat.test',
        apiKey: 'enterprise-pat',
        projectPath: '/home/user/myproject',
        sign: true,
      });

      await action.handler(ctx as unknown as Parameters<typeof action.handler>[0]);

      const [, opts] = mockFetch.mock.calls[0];
      const body = JSON.parse(opts.body as string);
      expect(body.project_id).toBe('/home/user/myproject');
      expect(body.auto_sign).toBe(true);

      expect(ctx._outputs.snapshotId).toBe('99');
      expect(ctx._outputs.artifactCount).toBe(3);
    });

    it('includes Authorization header when apiKey is set', async () => {
      const bomResp = {
        id: 1,
        owner_type: 'enterprise',
        created_at: '2026-03-13T12:00:00Z',
        bom: { artifact_count: 0, generated_at: '2026-03-13T12:00:00Z' },
        signed: false,
      };
      mockFetch.mockResolvedValueOnce(mockResponse(bomResp, 201, true));

      const ctx = makeCtx({
        apiBaseUrl: 'http://sam.internal',
        apiKey: 'my-pat',
      });

      await action.handler(ctx as unknown as Parameters<typeof action.handler>[0]);

      const [, opts] = mockFetch.mock.calls[0];
      expect((opts.headers as Record<string, string>)['Authorization']).toBe(
        'Bearer my-pat',
      );
    });
  });

  describe('error handling', () => {
    it('throws when the API returns a non-OK status', async () => {
      mockFetch.mockResolvedValueOnce(
        mockResponse({ detail: 'BOM generation failed: db error' }, 500, false),
      );

      const ctx = makeCtx({
        apiBaseUrl: 'http://skillmeat.test',
      });

      await expect(
        action.handler(ctx as unknown as Parameters<typeof action.handler>[0]),
      ).rejects.toThrow('SkillMeat BOM generate API returned 500');
    });

    it('throws when apiBaseUrl is missing and config has no skillmeat.baseUrl', async () => {
      const ctx = makeCtx({});

      await expect(
        action.handler(ctx as unknown as Parameters<typeof action.handler>[0]),
      ).rejects.toThrow('baseUrl is required');
    });

    it('uses skillmeat.baseUrl from config when apiBaseUrl input is absent', async () => {
      const bomResp = {
        id: 5,
        owner_type: 'user',
        created_at: '2026-03-13T09:00:00Z',
        bom: { artifact_count: 2, generated_at: '2026-03-13T09:00:00Z' },
        signed: false,
      };
      mockFetch.mockResolvedValueOnce(mockResponse(bomResp, 201, true));

      const ctx = makeCtx({});
      ctx.config.getOptionalString = jest.fn((key: string) =>
        key === 'skillmeat.baseUrl' ? 'http://from-config.test' : undefined,
      );

      await action.handler(ctx as unknown as Parameters<typeof action.handler>[0]);

      const [url] = mockFetch.mock.calls[0];
      expect(url).toBe('http://from-config.test/api/v1/bom/generate');
    });

    it('strips trailing slash from baseUrl before building the URL', async () => {
      const bomResp = {
        id: 6,
        owner_type: 'user',
        created_at: '2026-03-13T08:00:00Z',
        bom: { artifact_count: 0, generated_at: '2026-03-13T08:00:00Z' },
        signed: false,
      };
      mockFetch.mockResolvedValueOnce(mockResponse(bomResp, 201, true));

      const ctx = makeCtx({
        apiBaseUrl: 'http://skillmeat.test/',
      });

      await action.handler(ctx as unknown as Parameters<typeof action.handler>[0]);

      const [url] = mockFetch.mock.calls[0];
      expect(url).toBe('http://skillmeat.test/api/v1/bom/generate');
    });
  });
});
