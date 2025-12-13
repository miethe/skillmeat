/**
 * Tests for useGroups hooks
 */

import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { groupKeys } from '@/hooks/use-groups';

describe('groupKeys', () => {
  it('generates correct query keys', () => {
    expect(groupKeys.all).toEqual(['groups']);
    expect(groupKeys.lists()).toEqual(['groups', 'list']);
    expect(groupKeys.list('collection-1')).toEqual(['groups', 'list', { collectionId: 'collection-1' }]);
    expect(groupKeys.details()).toEqual(['groups', 'detail']);
    expect(groupKeys.detail('group-1')).toEqual(['groups', 'detail', 'group-1']);
    expect(groupKeys.artifacts('group-1')).toEqual(['groups', 'detail', 'group-1', 'artifacts']);
  });

  it('generates unique keys for different collections', () => {
    const key1 = groupKeys.list('collection-1');
    const key2 = groupKeys.list('collection-2');
    expect(key1).not.toEqual(key2);
  });

  it('generates unique keys for different groups', () => {
    const key1 = groupKeys.detail('group-1');
    const key2 = groupKeys.detail('group-2');
    expect(key1).not.toEqual(key2);
  });
});

// Note: Full hook tests would require mocking the API
// These tests verify the query key factory which is critical for cache management
