'use client';

/**
 * Custom hooks for context pack operations using TanStack Query
 *
 * Context packs are token-budget-aware compilations of memory items into
 * structured markdown suitable for injection into agent prompts.
 *
 * Both operations are mutations (POST endpoints):
 * - usePreviewContextPack (read-only preview of pack contents)
 * - useGenerateContextPack (full pack generation with markdown)
 */

import { useMutation } from '@tanstack/react-query';
import type { UseMutationOptions } from '@tanstack/react-query';
import { previewContextPack, generateContextPack } from '@/lib/api/context-packs';
import type { ContextPackPreviewRequest } from '@/sdk/models/ContextPackPreviewRequest';
import type { ContextPackPreviewResponse } from '@/sdk/models/ContextPackPreviewResponse';
import type { ContextPackGenerateRequest } from '@/sdk/models/ContextPackGenerateRequest';
import type { ContextPackGenerateResponse } from '@/sdk/models/ContextPackGenerateResponse';

// ============================================================================
// MUTATION HOOKS
// ============================================================================

export function usePreviewContextPack(
  options?: Pick<
    UseMutationOptions<
      ContextPackPreviewResponse,
      Error,
      { projectId: string; data: ContextPackPreviewRequest }
    >,
    'onSuccess' | 'onError'
  >
) {
  return useMutation({
    mutationFn: async ({
      projectId,
      data,
    }: {
      projectId: string;
      data: ContextPackPreviewRequest;
    }): Promise<ContextPackPreviewResponse> => {
      return previewContextPack(projectId, data);
    },
    onSuccess: options?.onSuccess,
    onError: options?.onError,
  });
}

export function useGenerateContextPack(
  options?: Pick<
    UseMutationOptions<
      ContextPackGenerateResponse,
      Error,
      { projectId: string; data: ContextPackGenerateRequest }
    >,
    'onSuccess' | 'onError'
  >
) {
  return useMutation({
    mutationFn: async ({
      projectId,
      data,
    }: {
      projectId: string;
      data: ContextPackGenerateRequest;
    }): Promise<ContextPackGenerateResponse> => {
      return generateContextPack(projectId, data);
    },
    onSuccess: options?.onSuccess,
    onError: options?.onError,
  });
}
