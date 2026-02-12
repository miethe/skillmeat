/**
 * Unit tests for collection API helpers.
 */

import { fetchCollectionArtifactsPaginated } from '@/lib/api/collections';

describe('fetchCollectionArtifactsPaginated', () => {
  beforeEach(() => {
    jest.resetAllMocks();
  });

  it('includes group_id and include_groups params when provided', async () => {
    const mockResponse = {
      items: [],
      page_info: {
        has_next_page: false,
        has_previous_page: false,
        start_cursor: null,
        end_cursor: null,
        total_count: 0,
      },
    };

    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => mockResponse,
    } as Response);

    await fetchCollectionArtifactsPaginated('collection-123', {
      limit: 20,
      after: 'cursor-1',
      artifact_type: 'skill',
      group_id: 'group-9',
      include_groups: true,
    });

    expect(global.fetch).toHaveBeenCalledTimes(1);
    const calledUrl = (global.fetch as jest.Mock).mock.calls[0][0] as string;
    expect(calledUrl).toContain('/api/v1/user-collections/collection-123/artifacts?');
    expect(calledUrl).toContain('limit=20');
    expect(calledUrl).toContain('after=cursor-1');
    expect(calledUrl).toContain('artifact_type=skill');
    expect(calledUrl).toContain('group_id=group-9');
    expect(calledUrl).toContain('include_groups=true');
  });
});
