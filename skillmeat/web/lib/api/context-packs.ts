/**
 * Context packs API service functions
 */
import { apiRequest } from '@/lib/api';
import type { ContextPackPreviewRequest } from '@/sdk/models/ContextPackPreviewRequest';
import type { ContextPackPreviewResponse } from '@/sdk/models/ContextPackPreviewResponse';
import type { ContextPackGenerateRequest } from '@/sdk/models/ContextPackGenerateRequest';
import type { ContextPackGenerateResponse } from '@/sdk/models/ContextPackGenerateResponse';

export async function previewContextPack(
  projectId: string,
  data: ContextPackPreviewRequest
): Promise<ContextPackPreviewResponse> {
  return apiRequest<ContextPackPreviewResponse>(
    `/context-packs/preview?project_id=${encodeURIComponent(projectId)}`,
    {
      method: 'POST',
      body: JSON.stringify(data),
    }
  );
}

export async function generateContextPack(
  projectId: string,
  data: ContextPackGenerateRequest
): Promise<ContextPackGenerateResponse> {
  return apiRequest<ContextPackGenerateResponse>(
    `/context-packs/generate?project_id=${encodeURIComponent(projectId)}`,
    {
      method: 'POST',
      body: JSON.stringify(data),
    }
  );
}
