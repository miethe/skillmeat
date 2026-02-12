/**
 * @jest-environment jsdom
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { GroupsPageClient } from '@/app/groups/components/groups-page-client';
import { useCollectionContext, useCreateGroup, useDeleteGroup, useGroups, useToast, useUpdateGroup } from '@/hooks';
import type { Group } from '@/types/groups';

jest.mock('@/hooks', () => ({
  useCollectionContext: jest.fn(),
  useGroups: jest.fn(),
  useToast: jest.fn(),
  useCreateGroup: jest.fn(),
  useUpdateGroup: jest.fn(),
  useDeleteGroup: jest.fn(),
  useCopyGroup: jest.fn(),
}));

// Keep tests focused on page behavior; avoid deep dialog internals.
jest.mock('@/components/collection/collection-switcher', () => ({
  CollectionSwitcher: ({ className }: { className?: string }) => (
    <button type="button" className={className}>
      CollectionSwitcher
    </button>
  ),
}));

jest.mock('@/components/collection/copy-group-dialog', () => ({
  CopyGroupDialog: ({ open }: { open: boolean }) => (open ? <div>Copy dialog</div> : null),
}));

// Mock next/navigation
const mockPush = jest.fn();
let mockSearchParams = new URLSearchParams();

jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
    replace: jest.fn(),
  }),
  useSearchParams: () => mockSearchParams,
}));

// Mock next/link
jest.mock('next/link', () => {
  return ({ children, href, ...rest }: { children: React.ReactNode; href: string }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  );
});

const mockUseCollectionContext = useCollectionContext as jest.MockedFunction<typeof useCollectionContext>;
const mockUseGroups = useGroups as jest.MockedFunction<typeof useGroups>;
const mockUseToast = useToast as jest.MockedFunction<typeof useToast>;
const mockUseCreateGroup = useCreateGroup as jest.MockedFunction<typeof useCreateGroup>;
const mockUseUpdateGroup = useUpdateGroup as jest.MockedFunction<typeof useUpdateGroup>;
const mockUseDeleteGroup = useDeleteGroup as jest.MockedFunction<typeof useDeleteGroup>;

describe('GroupsPageClient', () => {
  let queryClient: QueryClient;

  const mockGroups: Group[] = [
    {
      id: 'group-1',
      collection_id: 'collection-1',
      name: 'Development Tools',
      description: 'Tools for building and debugging',
      tags: ['frontend', 'critical'],
      color: 'blue',
      icon: 'layers',
      position: 0,
      artifact_count: 5,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-02T00:00:00Z',
    },
    {
      id: 'group-2',
      collection_id: 'collection-1',
      name: 'Research',
      description: 'Reference docs and studies',
      tags: ['notes'],
      color: 'green',
      icon: 'book',
      position: 1,
      artifact_count: 2,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-03T00:00:00Z',
    },
  ];

  beforeEach(() => {
    jest.clearAllMocks();
    mockSearchParams = new URLSearchParams();
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });

    mockUseToast.mockReturnValue({ toast: jest.fn() } as any);
    mockUseCreateGroup.mockReturnValue({ mutateAsync: jest.fn(), isPending: false } as any);
    mockUseUpdateGroup.mockReturnValue({ mutateAsync: jest.fn(), isPending: false } as any);
    mockUseDeleteGroup.mockReturnValue({ mutateAsync: jest.fn(), isPending: false } as any);

    mockUseCollectionContext.mockReturnValue({
      collections: [{ id: 'collection-1', name: 'Main', version: '1.0.0', artifact_count: 10, created_at: '', updated_at: '' }] as any,
      selectedCollectionId: 'collection-1',
      selectedGroupId: null,
      currentCollection: null,
      currentGroups: mockGroups,
      isLoadingCollections: false,
      isLoadingCollection: false,
      isLoadingGroups: false,
      collectionsError: null,
      collectionError: null,
      groupsError: null,
      setSelectedCollectionId: jest.fn(),
      setSelectedGroupId: jest.fn(),
      refreshCollections: jest.fn(),
      refreshGroups: jest.fn(),
    });

    mockUseGroups.mockReturnValue({
      data: { groups: mockGroups, total: mockGroups.length },
      isLoading: false,
      error: null,
    } as any);
  });

  const renderComponent = () =>
    render(
      <QueryClientProvider client={queryClient}>
        <GroupsPageClient />
      </QueryClientProvider>
    );

  it('renders no collections state', () => {
    mockUseCollectionContext.mockReturnValue({
      collections: [],
      selectedCollectionId: null,
      selectedGroupId: null,
      currentCollection: null,
      currentGroups: [],
      isLoadingCollections: false,
      isLoadingCollection: false,
      isLoadingGroups: false,
      collectionsError: null,
      collectionError: null,
      groupsError: null,
      setSelectedCollectionId: jest.fn(),
      setSelectedGroupId: jest.fn(),
      refreshCollections: jest.fn(),
      refreshGroups: jest.fn(),
    });

    renderComponent();
    expect(screen.getByText(/No collections yet/i)).toBeInTheDocument();
  });

  it('renders select collection state', () => {
    mockUseCollectionContext.mockReturnValue({
      collections: [{ id: 'collection-1', name: 'Main', version: '1.0.0', artifact_count: 10, created_at: '', updated_at: '' }] as any,
      selectedCollectionId: null,
      selectedGroupId: null,
      currentCollection: null,
      currentGroups: [],
      isLoadingCollections: false,
      isLoadingCollection: false,
      isLoadingGroups: false,
      collectionsError: null,
      collectionError: null,
      groupsError: null,
      setSelectedCollectionId: jest.fn(),
      setSelectedGroupId: jest.fn(),
      refreshCollections: jest.fn(),
      refreshGroups: jest.fn(),
    });

    renderComponent();
    expect(screen.getByText(/Select a collection/i)).toBeInTheDocument();
  });

  it('renders groups as cards', () => {
    renderComponent();
    expect(screen.getByText('Development Tools')).toBeInTheDocument();
    expect(screen.getByText('Research')).toBeInTheDocument();
    expect(screen.getAllByRole('link', { name: /Open Artifacts/i })).toHaveLength(2);
  });

  it('filters groups by search input', () => {
    renderComponent();
    fireEvent.change(screen.getByRole('textbox', { name: /Search groups/i }), {
      target: { value: 'research' },
    });

    expect(screen.getByText('Research')).toBeInTheDocument();
    expect(screen.queryByText('Development Tools')).not.toBeInTheDocument();
  });

  it('shows no matching groups state when search does not match', () => {
    renderComponent();
    fireEvent.change(screen.getByRole('textbox', { name: /Search groups/i }), {
      target: { value: 'missing-group' },
    });
    expect(screen.getByText(/No matching groups/i)).toBeInTheDocument();
  });
});
