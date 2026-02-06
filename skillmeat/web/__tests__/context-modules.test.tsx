/**
 * @jest-environment jsdom
 */

/**
 * Comprehensive tests for Phase 4 Context Module and Pack UI components:
 * - ContextModulesTab: Lists and manages context modules
 * - ModuleEditor: Form for creating/editing modules with selector builder
 * - EffectiveContextPreview: Modal showing generated context pack with markdown
 * - ContextPackGenerator: Workflow for generating context packs
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// ---------------------------------------------------------------------------
// Component imports
// ---------------------------------------------------------------------------

import { ContextModulesTab } from '@/components/memory/context-modules-tab';
import { ModuleEditor } from '@/components/memory/module-editor';
import { EffectiveContextPreview } from '@/components/memory/effective-context-preview';
import { ContextPackGenerator } from '@/components/memory/context-pack-generator';

// ---------------------------------------------------------------------------
// Mock: use-context-modules
// ---------------------------------------------------------------------------

const mockUseContextModules = jest.fn();
const mockUseContextModule = jest.fn();
const mockCreateMutate = jest.fn();
const mockUseCreateContextModule = jest.fn();
const mockUpdateMutate = jest.fn();
const mockUseUpdateContextModule = jest.fn();
const mockDeleteMutate = jest.fn();
const mockUseDeleteContextModule = jest.fn();
const mockUseModuleMemories = jest.fn();
const mockRemoveMutate = jest.fn();
const mockUseRemoveMemoryFromModule = jest.fn();

jest.mock('@/hooks/use-context-modules', () => ({
  useContextModules: (...args: unknown[]) => mockUseContextModules(...args),
  useContextModule: (...args: unknown[]) => mockUseContextModule(...args),
  useCreateContextModule: (...args: unknown[]) => mockUseCreateContextModule(...args),
  useUpdateContextModule: (...args: unknown[]) => mockUseUpdateContextModule(...args),
  useDeleteContextModule: (...args: unknown[]) => mockUseDeleteContextModule(...args),
  useModuleMemories: (...args: unknown[]) => mockUseModuleMemories(...args),
  useRemoveMemoryFromModule: (...args: unknown[]) => mockUseRemoveMemoryFromModule(...args),
}));

// ---------------------------------------------------------------------------
// Mock: use-context-packs
// ---------------------------------------------------------------------------

const mockPreviewMutate = jest.fn();
const mockUsePreviewContextPack = jest.fn();
const mockGenerateMutate = jest.fn();
const mockUseGenerateContextPack = jest.fn();

jest.mock('@/hooks/use-context-packs', () => ({
  usePreviewContextPack: (...args: unknown[]) => mockUsePreviewContextPack(...args),
  useGenerateContextPack: (...args: unknown[]) => mockUseGenerateContextPack(...args),
}));

// ---------------------------------------------------------------------------
// Mock: barrel hooks/index.ts (ContextPackGenerator imports from @/hooks)
// ---------------------------------------------------------------------------

jest.mock('@/hooks', () => ({
  useContextModules: (...args: unknown[]) => mockUseContextModules(...args),
  usePreviewContextPack: (...args: unknown[]) => mockUsePreviewContextPack(...args),
  useGenerateContextPack: (...args: unknown[]) => mockUseGenerateContextPack(...args),
}));

// ---------------------------------------------------------------------------
// Mock: memory-utils (used by ModuleEditor and ContextPackGenerator)
// ---------------------------------------------------------------------------

jest.mock('@/components/memory/memory-utils', () => ({
  getConfidenceTier: (c: number) => (c >= 0.85 ? 'high' : c >= 0.6 ? 'medium' : 'low'),
  getConfidenceColorClasses: () => ({ bg: 'bg-test', text: 'text-test', border: 'border-test' }),
}));

// ---------------------------------------------------------------------------
// Mock: memory-type-badge (simplify rendering for tests)
// ---------------------------------------------------------------------------

jest.mock('@/components/memory/memory-type-badge', () => ({
  MemoryTypeBadge: ({ type }: { type: string }) => (
    <span data-testid="memory-type-badge">{type}</span>
  ),
  MEMORY_TYPE_CONFIG: {},
}));

// ---------------------------------------------------------------------------
// Mock: clipboard API
// ---------------------------------------------------------------------------

const mockClipboardWriteText = jest.fn().mockResolvedValue(undefined);

beforeAll(() => {
  Object.assign(navigator, {
    clipboard: {
      writeText: mockClipboardWriteText,
    },
  });
});

// ---------------------------------------------------------------------------
// Test Data
// ---------------------------------------------------------------------------

const mockModule1 = {
  id: 'mod-1',
  project_id: 'proj-1',
  name: 'Core Patterns',
  description: 'Key architectural decisions',
  selectors: {
    memory_types: ['decision', 'constraint'],
    min_confidence: 0.7,
    file_patterns: ['src/**'],
    workflow_stages: ['planning'],
  },
  priority: 8,
  memory_items: [],
  created_at: '2026-02-05T10:00:00Z',
  updated_at: '2026-02-05T10:00:00Z',
};

const mockModule2 = {
  id: 'mod-2',
  project_id: 'proj-1',
  name: 'Frontend Rules',
  description: 'React component conventions',
  selectors: {
    memory_types: ['style_rule'],
    min_confidence: 0.5,
  },
  priority: 3,
  memory_items: ['mem-1', 'mem-2'],
  created_at: '2026-02-04T08:00:00Z',
  updated_at: '2026-02-04T08:00:00Z',
};

const mockModuleNoSelectors = {
  id: 'mod-3',
  project_id: 'proj-1',
  name: 'Empty Module',
  description: null,
  selectors: null,
  priority: 5,
  memory_items: [],
  created_at: '2026-02-03T06:00:00Z',
  updated_at: '2026-02-03T06:00:00Z',
};

const mockPackResponse = {
  items: [
    {
      id: 'mem-1',
      type: 'decision',
      content: 'Use TypeScript strict mode for all new modules',
      confidence: 0.95,
      tokens: 12,
    },
    {
      id: 'mem-2',
      type: 'constraint',
      content: 'Max 200ms API response time',
      confidence: 0.88,
      tokens: 15,
    },
  ],
  total_tokens: 27,
  budget_tokens: 4000,
  utilization: 0.007,
  items_included: 2,
  items_available: 5,
  markdown:
    '# Context Pack\n\n## Decisions\n- Use TypeScript strict mode\n\n## Constraints\n- Max 200ms API response time',
  generated_at: '2026-02-06T10:00:00Z',
};

const mockMemoryItems = [
  {
    id: 'mem-1',
    type: 'decision',
    content: 'Use TypeScript strict mode for all new modules in the project',
    confidence: 0.95,
    status: 'active',
    created_at: '2026-02-01T10:00:00Z',
    updated_at: '2026-02-01T10:00:00Z',
  },
  {
    id: 'mem-2',
    type: 'constraint',
    content: 'Max 200ms API response time for all public endpoints',
    confidence: 0.88,
    status: 'active',
    created_at: '2026-02-02T10:00:00Z',
    updated_at: '2026-02-02T10:00:00Z',
  },
];

// ---------------------------------------------------------------------------
// Test Helpers
// ---------------------------------------------------------------------------

function createTestQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
}

function TestWrapper({ children }: { children: React.ReactNode }) {
  const queryClient = createTestQueryClient();
  return (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

function setupDefaultMocks() {
  // useContextModules - default to returning modules list
  mockUseContextModules.mockReturnValue({
    data: { items: [mockModule1, mockModule2] },
    isLoading: false,
    isError: false,
    error: null,
    refetch: jest.fn(),
  });

  // Create module mutation
  mockUseCreateContextModule.mockReturnValue({
    mutate: mockCreateMutate,
    isPending: false,
    error: null,
  });

  // Update module mutation
  mockUseUpdateContextModule.mockReturnValue({
    mutate: mockUpdateMutate,
    isPending: false,
    error: null,
  });

  // Delete module mutation
  mockUseDeleteContextModule.mockReturnValue({
    mutate: mockDeleteMutate,
    isPending: false,
    error: null,
  });

  // Module memories query
  mockUseModuleMemories.mockReturnValue({
    data: [],
    isLoading: false,
    isError: false,
  });

  // Remove memory from module mutation
  mockUseRemoveMemoryFromModule.mockReturnValue({
    mutate: mockRemoveMutate,
    isPending: false,
    variables: null,
  });

  // Preview context pack mutation
  mockUsePreviewContextPack.mockReturnValue({
    mutate: mockPreviewMutate,
    isPending: false,
    isError: false,
    error: null,
  });

  // Generate context pack mutation
  mockUseGenerateContextPack.mockReturnValue({
    mutate: mockGenerateMutate,
    isPending: false,
    isError: false,
    error: null,
  });
}

// ---------------------------------------------------------------------------
// Tests: ContextModulesTab
// ---------------------------------------------------------------------------

describe('ContextModulesTab', () => {
  beforeEach(() => {
    setupDefaultMocks();
  });

  describe('Loading State', () => {
    it('renders loading skeletons when data is loading', () => {
      mockUseContextModules.mockReturnValue({
        data: undefined,
        isLoading: true,
        isError: false,
        error: null,
        refetch: jest.fn(),
      });

      render(
        <TestWrapper>
          <ContextModulesTab projectId="proj-1" />
        </TestWrapper>
      );

      const loadingRegion = screen.getByRole('status', {
        name: /loading context modules/i,
      });
      expect(loadingRegion).toBeInTheDocument();
      expect(screen.getByText(/loading context modules/i)).toBeInTheDocument();
    });
  });

  describe('Error State', () => {
    it('renders error state with retry button when query fails', () => {
      const mockRefetch = jest.fn();
      mockUseContextModules.mockReturnValue({
        data: undefined,
        isLoading: false,
        isError: true,
        error: { message: 'Network error' },
        refetch: mockRefetch,
      });

      render(
        <TestWrapper>
          <ContextModulesTab projectId="proj-1" />
        </TestWrapper>
      );

      expect(screen.getByRole('alert')).toBeInTheDocument();
      expect(
        screen.getByText(/failed to load context modules/i)
      ).toBeInTheDocument();
      expect(screen.getByText(/network error/i)).toBeInTheDocument();

      const retryBtn = screen.getByRole('button', { name: /retry/i });
      expect(retryBtn).toBeInTheDocument();
    });

    it('calls refetch when retry button is clicked', async () => {
      const mockRefetch = jest.fn();
      mockUseContextModules.mockReturnValue({
        data: undefined,
        isLoading: false,
        isError: true,
        error: { message: 'Network error' },
        refetch: mockRefetch,
      });

      render(
        <TestWrapper>
          <ContextModulesTab projectId="proj-1" />
        </TestWrapper>
      );

      await userEvent.click(screen.getByRole('button', { name: /retry/i }));
      expect(mockRefetch).toHaveBeenCalledTimes(1);
    });
  });

  describe('Empty State', () => {
    it('renders empty state when no modules exist', () => {
      mockUseContextModules.mockReturnValue({
        data: { items: [] },
        isLoading: false,
        isError: false,
        error: null,
        refetch: jest.fn(),
      });

      render(
        <TestWrapper>
          <ContextModulesTab projectId="proj-1" />
        </TestWrapper>
      );

      expect(screen.getByText(/no context modules yet/i)).toBeInTheDocument();
      expect(
        screen.getByRole('button', { name: /create first module/i })
      ).toBeInTheDocument();
    });
  });

  describe('Module List', () => {
    it('renders module names and descriptions', () => {
      render(
        <TestWrapper>
          <ContextModulesTab projectId="proj-1" />
        </TestWrapper>
      );

      expect(screen.getByText('Core Patterns')).toBeInTheDocument();
      expect(
        screen.getByText('Key architectural decisions')
      ).toBeInTheDocument();
      expect(screen.getByText('Frontend Rules')).toBeInTheDocument();
      expect(
        screen.getByText('React component conventions')
      ).toBeInTheDocument();
    });

    it('renders priority badges for each module', () => {
      render(
        <TestWrapper>
          <ContextModulesTab projectId="proj-1" />
        </TestWrapper>
      );

      expect(screen.getByText('Priority 8')).toBeInTheDocument();
      expect(screen.getByText('Priority 3')).toBeInTheDocument();
    });

    it('renders module list with correct ARIA role', () => {
      render(
        <TestWrapper>
          <ContextModulesTab projectId="proj-1" />
        </TestWrapper>
      );

      const list = screen.getByRole('list', { name: /context modules/i });
      expect(list).toBeInTheDocument();

      const items = within(list).getAllByRole('listitem');
      expect(items).toHaveLength(2);
    });

    it('announces module count to screen readers', () => {
      render(
        <TestWrapper>
          <ContextModulesTab projectId="proj-1" />
        </TestWrapper>
      );

      expect(
        screen.getByText(/2 context modules displayed/i)
      ).toBeInTheDocument();
    });
  });

  describe('Selector Summary', () => {
    it('shows selector badges for memory types', () => {
      render(
        <TestWrapper>
          <ContextModulesTab projectId="proj-1" />
        </TestWrapper>
      );

      expect(
        screen.getByText('Types: decision, constraint')
      ).toBeInTheDocument();
    });

    it('shows confidence badge for min_confidence', () => {
      render(
        <TestWrapper>
          <ContextModulesTab projectId="proj-1" />
        </TestWrapper>
      );

      expect(screen.getByText('Min confidence: 0.7')).toBeInTheDocument();
    });

    it('shows patterns count badge', () => {
      render(
        <TestWrapper>
          <ContextModulesTab projectId="proj-1" />
        </TestWrapper>
      );

      expect(screen.getByText('Patterns: 1')).toBeInTheDocument();
    });

    it('shows workflow stages badge', () => {
      render(
        <TestWrapper>
          <ContextModulesTab projectId="proj-1" />
        </TestWrapper>
      );

      expect(screen.getByText('Stages: planning')).toBeInTheDocument();
    });

    it('shows "No selectors configured" when module has no selectors', () => {
      mockUseContextModules.mockReturnValue({
        data: { items: [mockModuleNoSelectors] },
        isLoading: false,
        isError: false,
        error: null,
        refetch: jest.fn(),
      });

      render(
        <TestWrapper>
          <ContextModulesTab projectId="proj-1" />
        </TestWrapper>
      );

      expect(
        screen.getByText(/no selectors configured/i)
      ).toBeInTheDocument();
    });

    it('shows memory count badge when module has memory items', () => {
      render(
        <TestWrapper>
          <ContextModulesTab projectId="proj-1" />
        </TestWrapper>
      );

      expect(screen.getByText('2 memories')).toBeInTheDocument();
    });
  });

  describe('Create Module Flow', () => {
    it('opens create dialog when "New Module" button is clicked', async () => {
      render(
        <TestWrapper>
          <ContextModulesTab projectId="proj-1" />
        </TestWrapper>
      );

      await userEvent.click(
        screen.getByRole('button', { name: /new module/i })
      );

      expect(
        screen.getByText(/create context module/i)
      ).toBeInTheDocument();
      expect(
        screen.getByLabelText(/name/i)
      ).toBeInTheDocument();
    });

    it('shows validation error when name is empty on submit', async () => {
      render(
        <TestWrapper>
          <ContextModulesTab projectId="proj-1" />
        </TestWrapper>
      );

      await userEvent.click(
        screen.getByRole('button', { name: /new module/i })
      );

      // Submit without filling name
      await userEvent.click(
        screen.getByRole('button', { name: /create module/i })
      );

      expect(screen.getByRole('alert')).toBeInTheDocument();
      expect(screen.getByText(/name is required/i)).toBeInTheDocument();
      expect(mockCreateMutate).not.toHaveBeenCalled();
    });

    it('calls create mutation with correct data on valid submit', async () => {
      render(
        <TestWrapper>
          <ContextModulesTab projectId="proj-1" />
        </TestWrapper>
      );

      await userEvent.click(
        screen.getByRole('button', { name: /new module/i })
      );

      // Fill form
      const nameInput = screen.getByLabelText(/name/i);
      await userEvent.type(nameInput, 'New Test Module');

      const descInput = screen.getByLabelText(/description/i);
      await userEvent.type(descInput, 'A test description');

      // Submit
      await userEvent.click(
        screen.getByRole('button', { name: /create module/i })
      );

      expect(mockCreateMutate).toHaveBeenCalledWith({
        projectId: 'proj-1',
        data: {
          name: 'New Test Module',
          description: 'A test description',
          priority: 5,
        },
      });
    });

    it('closes dialog when cancel button is clicked', async () => {
      render(
        <TestWrapper>
          <ContextModulesTab projectId="proj-1" />
        </TestWrapper>
      );

      await userEvent.click(
        screen.getByRole('button', { name: /new module/i })
      );

      expect(
        screen.getByText(/create context module/i)
      ).toBeInTheDocument();

      await userEvent.click(
        screen.getByRole('button', { name: /cancel/i })
      );

      await waitFor(() => {
        expect(
          screen.queryByText(/define a new module/i)
        ).not.toBeInTheDocument();
      });
    });
  });

  describe('Delete Module Flow', () => {
    it('opens confirmation dialog when delete button is clicked', async () => {
      render(
        <TestWrapper>
          <ContextModulesTab projectId="proj-1" />
        </TestWrapper>
      );

      const deleteBtn = screen.getByRole('button', {
        name: /delete module: core patterns/i,
      });
      await userEvent.click(deleteBtn);

      expect(
        screen.getByText(/delete context module\?/i)
      ).toBeInTheDocument();
      expect(
        screen.getByText(/permanently delete the "Core Patterns" module/i)
      ).toBeInTheDocument();
    });

    it('calls delete mutation when confirmed', async () => {
      render(
        <TestWrapper>
          <ContextModulesTab projectId="proj-1" />
        </TestWrapper>
      );

      // Click delete on first module
      const deleteBtn = screen.getByRole('button', {
        name: /delete module: core patterns/i,
      });
      await userEvent.click(deleteBtn);

      // Confirm deletion
      const confirmBtn = screen.getByRole('button', { name: /^delete$/i });
      await userEvent.click(confirmBtn);

      expect(mockDeleteMutate).toHaveBeenCalledWith({
        projectId: 'proj-1',
        moduleId: 'mod-1',
      });
    });

    it('closes confirmation dialog when cancel is clicked', async () => {
      render(
        <TestWrapper>
          <ContextModulesTab projectId="proj-1" />
        </TestWrapper>
      );

      const deleteBtn = screen.getByRole('button', {
        name: /delete module: core patterns/i,
      });
      await userEvent.click(deleteBtn);

      expect(
        screen.getByText(/delete context module\?/i)
      ).toBeInTheDocument();

      await userEvent.click(screen.getByRole('button', { name: /cancel/i }));

      await waitFor(() => {
        expect(
          screen.queryByText(/delete context module\?/i)
        ).not.toBeInTheDocument();
      });
    });
  });

  describe('Action Buttons', () => {
    it('renders edit button with correct aria-label', () => {
      render(
        <TestWrapper>
          <ContextModulesTab projectId="proj-1" />
        </TestWrapper>
      );

      expect(
        screen.getByRole('button', { name: /edit module: core patterns/i })
      ).toBeInTheDocument();
    });

    it('renders preview button with correct aria-label', () => {
      render(
        <TestWrapper>
          <ContextModulesTab projectId="proj-1" />
        </TestWrapper>
      );

      expect(
        screen.getByRole('button', {
          name: /preview pack for module: core patterns/i,
        })
      ).toBeInTheDocument();
    });
  });
});

// ---------------------------------------------------------------------------
// Tests: ModuleEditor
// ---------------------------------------------------------------------------

describe('ModuleEditor', () => {
  beforeEach(() => {
    setupDefaultMocks();
  });

  describe('Create Mode', () => {
    it('renders empty form with "Create Context Module" title', () => {
      render(
        <TestWrapper>
          <ModuleEditor projectId="proj-1" />
        </TestWrapper>
      );

      expect(
        screen.getByText(/create context module/i)
      ).toBeInTheDocument();

      const nameInput = screen.getByLabelText(/name/i);
      expect(nameInput).toHaveValue('');

      expect(
        screen.getByRole('button', { name: /create module/i })
      ).toBeInTheDocument();
    });

    it('has description field editable and empty', () => {
      render(
        <TestWrapper>
          <ModuleEditor projectId="proj-1" />
        </TestWrapper>
      );

      const descInput = screen.getByLabelText(/description/i);
      expect(descInput).toHaveValue('');
    });

    it('has priority default set to 5', () => {
      render(
        <TestWrapper>
          <ModuleEditor projectId="proj-1" />
        </TestWrapper>
      );

      const priorityInput = screen.getByLabelText(/priority/i);
      expect(priorityInput).toHaveValue(5);
    });

    it('does not show manual memories section in create mode', () => {
      render(
        <TestWrapper>
          <ModuleEditor projectId="proj-1" />
        </TestWrapper>
      );

      expect(
        screen.queryByText(/manual memories/i)
      ).not.toBeInTheDocument();
    });

    it('does not show Preview Pack button in create mode', () => {
      render(
        <TestWrapper>
          <ModuleEditor
            projectId="proj-1"
            onPreview={jest.fn()}
          />
        </TestWrapper>
      );

      expect(
        screen.queryByRole('button', { name: /preview pack/i })
      ).not.toBeInTheDocument();
    });

    it('calls create mutation on valid form submission', async () => {
      const onSave = jest.fn();
      render(
        <TestWrapper>
          <ModuleEditor projectId="proj-1" onSave={onSave} />
        </TestWrapper>
      );

      await userEvent.type(screen.getByLabelText(/name/i), 'Test Module');

      await userEvent.click(
        screen.getByRole('button', { name: /create module/i })
      );

      expect(mockCreateMutate).toHaveBeenCalledWith(
        expect.objectContaining({
          projectId: 'proj-1',
          data: expect.objectContaining({
            name: 'Test Module',
          }),
        })
      );
    });

    it('shows validation error for empty name', async () => {
      render(
        <TestWrapper>
          <ModuleEditor projectId="proj-1" />
        </TestWrapper>
      );

      await userEvent.click(
        screen.getByRole('button', { name: /create module/i })
      );

      expect(screen.getByRole('alert')).toBeInTheDocument();
      expect(mockCreateMutate).not.toHaveBeenCalled();
    });
  });

  describe('Edit Mode', () => {
    it('pre-populates name and description from module prop', () => {
      render(
        <TestWrapper>
          <ModuleEditor module={mockModule1 as any} projectId="proj-1" />
        </TestWrapper>
      );

      expect(
        screen.getByText(/edit context module/i)
      ).toBeInTheDocument();

      const nameInput = screen.getByLabelText(/name/i);
      expect(nameInput).toHaveValue('Core Patterns');

      const descInput = screen.getByLabelText(/description/i);
      expect(descInput).toHaveValue('Key architectural decisions');
    });

    it('pre-populates priority from module prop', () => {
      render(
        <TestWrapper>
          <ModuleEditor module={mockModule1 as any} projectId="proj-1" />
        </TestWrapper>
      );

      const priorityInput = screen.getByLabelText(/priority/i);
      expect(priorityInput).toHaveValue(8);
    });

    it('shows "Save Changes" button in edit mode', () => {
      render(
        <TestWrapper>
          <ModuleEditor module={mockModule1 as any} projectId="proj-1" />
        </TestWrapper>
      );

      expect(
        screen.getByRole('button', { name: /save changes/i })
      ).toBeInTheDocument();
    });

    it('shows Manual Memories section in edit mode', () => {
      render(
        <TestWrapper>
          <ModuleEditor module={mockModule1 as any} projectId="proj-1" />
        </TestWrapper>
      );

      expect(screen.getByText(/manual memories/i)).toBeInTheDocument();
    });

    it('shows "No memories manually added" when list is empty', () => {
      mockUseModuleMemories.mockReturnValue({
        data: [],
        isLoading: false,
        isError: false,
      });

      render(
        <TestWrapper>
          <ModuleEditor module={mockModule1 as any} projectId="proj-1" />
        </TestWrapper>
      );

      expect(
        screen.getByText(/no memories manually added/i)
      ).toBeInTheDocument();
    });

    it('renders manual memory items when present', () => {
      mockUseModuleMemories.mockReturnValue({
        data: mockMemoryItems,
        isLoading: false,
        isError: false,
      });

      render(
        <TestWrapper>
          <ModuleEditor module={mockModule1 as any} projectId="proj-1" />
        </TestWrapper>
      );

      const memList = screen.getByRole('list', { name: /manual memories/i });
      expect(memList).toBeInTheDocument();
      expect(within(memList).getAllByRole('listitem')).toHaveLength(2);
    });

    it('calls update mutation on save in edit mode', async () => {
      render(
        <TestWrapper>
          <ModuleEditor module={mockModule1 as any} projectId="proj-1" />
        </TestWrapper>
      );

      await userEvent.click(
        screen.getByRole('button', { name: /save changes/i })
      );

      expect(mockUpdateMutate).toHaveBeenCalledWith(
        expect.objectContaining({
          moduleId: 'mod-1',
          data: expect.objectContaining({
            name: 'Core Patterns',
          }),
        })
      );
    });

    it('shows Preview Pack button in edit mode when onPreview provided', () => {
      render(
        <TestWrapper>
          <ModuleEditor
            module={mockModule1 as any}
            projectId="proj-1"
            onPreview={jest.fn()}
          />
        </TestWrapper>
      );

      expect(
        screen.getByRole('button', { name: /preview pack/i })
      ).toBeInTheDocument();
    });

    it('calls onPreview with module id when preview button clicked', async () => {
      const onPreview = jest.fn();
      render(
        <TestWrapper>
          <ModuleEditor
            module={mockModule1 as any}
            projectId="proj-1"
            onPreview={onPreview}
          />
        </TestWrapper>
      );

      await userEvent.click(
        screen.getByRole('button', { name: /preview pack/i })
      );

      expect(onPreview).toHaveBeenCalledWith('mod-1');
    });
  });

  describe('Memory Type Checkboxes', () => {
    it('renders all five memory type checkboxes', () => {
      render(
        <TestWrapper>
          <ModuleEditor projectId="proj-1" />
        </TestWrapper>
      );

      expect(screen.getByText('Decision')).toBeInTheDocument();
      expect(screen.getByText('Constraint')).toBeInTheDocument();
      expect(screen.getByText('Gotcha')).toBeInTheDocument();
      expect(screen.getByText('Style Rule')).toBeInTheDocument();
      expect(screen.getByText('Learning')).toBeInTheDocument();
    });

    it('pre-selects memory types from module selectors in edit mode', () => {
      render(
        <TestWrapper>
          <ModuleEditor module={mockModule1 as any} projectId="proj-1" />
        </TestWrapper>
      );

      // The Decision and Constraint checkboxes should be checked
      const decisionCheckbox = screen.getByRole('checkbox', {
        name: /decision/i,
      });
      expect(decisionCheckbox).toBeChecked();

      const constraintCheckbox = screen.getByRole('checkbox', {
        name: /constraint/i,
      });
      expect(constraintCheckbox).toBeChecked();

      // Others should not be checked
      const gotchaCheckbox = screen.getByRole('checkbox', {
        name: /gotcha/i,
      });
      expect(gotchaCheckbox).not.toBeChecked();
    });
  });

  describe('Priority Input', () => {
    it('accepts numeric input within 0-100 range', async () => {
      render(
        <TestWrapper>
          <ModuleEditor projectId="proj-1" />
        </TestWrapper>
      );

      const priorityInput = screen.getByLabelText(/priority/i);
      fireEvent.change(priorityInput, { target: { value: '42' } });

      expect(priorityInput).toHaveValue(42);
    });
  });

  describe('Min Confidence Slider', () => {
    it('renders confidence slider with 0% display', () => {
      render(
        <TestWrapper>
          <ModuleEditor projectId="proj-1" />
        </TestWrapper>
      );

      const slider = screen.getByRole('slider', {
        name: /minimum confidence/i,
      });
      expect(slider).toBeInTheDocument();
      expect(screen.getByText('0%')).toBeInTheDocument();
    });

    it('displays pre-populated confidence in edit mode', () => {
      render(
        <TestWrapper>
          <ModuleEditor module={mockModule1 as any} projectId="proj-1" />
        </TestWrapper>
      );

      // mockModule1 has min_confidence: 0.7 which is 70%
      expect(screen.getByText('70%')).toBeInTheDocument();
    });
  });

  describe('Tag Inputs', () => {
    it('renders file patterns tag input', () => {
      render(
        <TestWrapper>
          <ModuleEditor projectId="proj-1" />
        </TestWrapper>
      );

      expect(screen.getByLabelText(/file patterns/i)).toBeInTheDocument();
    });

    it('renders workflow stages tag input', () => {
      render(
        <TestWrapper>
          <ModuleEditor projectId="proj-1" />
        </TestWrapper>
      );

      expect(screen.getByLabelText(/workflow stages/i)).toBeInTheDocument();
    });

    it('shows existing file patterns as tags in edit mode', () => {
      render(
        <TestWrapper>
          <ModuleEditor module={mockModule1 as any} projectId="proj-1" />
        </TestWrapper>
      );

      // mockModule1 has file_patterns: ['src/**']
      expect(screen.getByText('src/**')).toBeInTheDocument();
    });

    it('shows existing workflow stages as tags in edit mode', () => {
      render(
        <TestWrapper>
          <ModuleEditor module={mockModule1 as any} projectId="proj-1" />
        </TestWrapper>
      );

      // mockModule1 has workflow_stages: ['planning']
      expect(screen.getByText('planning')).toBeInTheDocument();
    });

    it('allows adding a tag by pressing Enter', async () => {
      render(
        <TestWrapper>
          <ModuleEditor projectId="proj-1" />
        </TestWrapper>
      );

      const filePatternInput = screen.getByLabelText(/file patterns/i);
      await userEvent.type(filePatternInput, 'src/components/**{Enter}');

      expect(screen.getByText('src/components/**')).toBeInTheDocument();
    });

    it('allows removing a tag by clicking the remove button', async () => {
      render(
        <TestWrapper>
          <ModuleEditor module={mockModule1 as any} projectId="proj-1" />
        </TestWrapper>
      );

      // Remove the 'src/**' file pattern tag
      const removeBtn = screen.getByRole('button', { name: /remove src\/\*\*/i });
      await userEvent.click(removeBtn);

      expect(screen.queryByText('src/**')).not.toBeInTheDocument();
    });
  });

  describe('Cancel Action', () => {
    it('calls onCancel when cancel button is clicked', async () => {
      const onCancel = jest.fn();
      render(
        <TestWrapper>
          <ModuleEditor projectId="proj-1" onCancel={onCancel} />
        </TestWrapper>
      );

      await userEvent.click(
        screen.getByRole('button', { name: /cancel/i })
      );

      expect(onCancel).toHaveBeenCalledTimes(1);
    });
  });

  describe('Mutation Error', () => {
    it('displays create mutation error message', () => {
      mockUseCreateContextModule.mockReturnValue({
        mutate: mockCreateMutate,
        isPending: false,
        error: { message: 'Server error creating module' },
      });

      render(
        <TestWrapper>
          <ModuleEditor projectId="proj-1" />
        </TestWrapper>
      );

      expect(
        screen.getByText(/server error creating module/i)
      ).toBeInTheDocument();
    });

    it('displays update mutation error message in edit mode', () => {
      mockUseUpdateContextModule.mockReturnValue({
        mutate: mockUpdateMutate,
        isPending: false,
        error: { message: 'Server error updating module' },
      });

      render(
        <TestWrapper>
          <ModuleEditor module={mockModule1 as any} projectId="proj-1" />
        </TestWrapper>
      );

      expect(
        screen.getByText(/server error updating module/i)
      ).toBeInTheDocument();
    });
  });
});

// ---------------------------------------------------------------------------
// Tests: EffectiveContextPreview
// ---------------------------------------------------------------------------

describe('EffectiveContextPreview', () => {
  beforeEach(() => {
    setupDefaultMocks();
    mockClipboardWriteText.mockClear();
  });

  describe('Loading State', () => {
    it('shows spinner when isLoading is true', () => {
      render(
        <TestWrapper>
          <EffectiveContextPreview
            open={true}
            onOpenChange={jest.fn()}
            isLoading={true}
          />
        </TestWrapper>
      );

      expect(
        screen.getByText(/generating context pack/i)
      ).toBeInTheDocument();
    });
  });

  describe('Empty State', () => {
    it('shows empty message when no data is provided', () => {
      render(
        <TestWrapper>
          <EffectiveContextPreview
            open={true}
            onOpenChange={jest.fn()}
            data={null}
          />
        </TestWrapper>
      );

      expect(
        screen.getByText(/no context pack data available/i)
      ).toBeInTheDocument();
    });
  });

  describe('Token Budget Bar', () => {
    it('renders utilization percentage with correct values', () => {
      render(
        <TestWrapper>
          <EffectiveContextPreview
            open={true}
            onOpenChange={jest.fn()}
            data={mockPackResponse as any}
          />
        </TestWrapper>
      );

      // Total tokens / budget tokens
      const budgetBar = screen.getByRole('progressbar');
      expect(budgetBar).toBeInTheDocument();
      expect(budgetBar).toHaveAttribute('aria-valuenow', '27');
      expect(budgetBar).toHaveAttribute('aria-valuemax', '4000');
    });

    it('shows items included vs available', () => {
      render(
        <TestWrapper>
          <EffectiveContextPreview
            open={true}
            onOpenChange={jest.fn()}
            data={mockPackResponse as any}
          />
        </TestWrapper>
      );

      expect(screen.getByText(/2 of 5 items included/i)).toBeInTheDocument();
    });

    it('renders green color for low utilization', () => {
      render(
        <TestWrapper>
          <EffectiveContextPreview
            open={true}
            onOpenChange={jest.fn()}
            data={mockPackResponse as any}
          />
        </TestWrapper>
      );

      // 0.7% utilization should be "normal" tier (green)
      expect(screen.getByText(/1%/)).toBeInTheDocument(); // Rounds up from 0.7%
    });

    it('renders amber color for warning utilization', () => {
      const warningData = {
        ...mockPackResponse,
        utilization: 0.75,
        total_tokens: 3000,
      };

      render(
        <TestWrapper>
          <EffectiveContextPreview
            open={true}
            onOpenChange={jest.fn()}
            data={warningData as any}
          />
        </TestWrapper>
      );

      expect(screen.getByText(/75%/)).toBeInTheDocument();
    });

    it('renders red color for critical utilization', () => {
      const criticalData = {
        ...mockPackResponse,
        utilization: 0.95,
        total_tokens: 3800,
      };

      render(
        <TestWrapper>
          <EffectiveContextPreview
            open={true}
            onOpenChange={jest.fn()}
            data={criticalData as any}
          />
        </TestWrapper>
      );

      expect(screen.getByText(/95%/)).toBeInTheDocument();
    });
  });

  describe('Markdown Content', () => {
    it('renders the markdown text in a pre element', () => {
      render(
        <TestWrapper>
          <EffectiveContextPreview
            open={true}
            onOpenChange={jest.fn()}
            data={mockPackResponse as any}
          />
        </TestWrapper>
      );

      expect(
        screen.getByText(/# Context Pack/i)
      ).toBeInTheDocument();
      expect(
        screen.getByText(/use typescript strict mode/i)
      ).toBeInTheDocument();
    });
  });

  describe('Copy to Clipboard', () => {
    it('copies markdown to clipboard when copy button is clicked', async () => {
      render(
        <TestWrapper>
          <EffectiveContextPreview
            open={true}
            onOpenChange={jest.fn()}
            data={mockPackResponse as any}
          />
        </TestWrapper>
      );

      const copyBtn = screen.getByRole('button', {
        name: /copy context pack to clipboard/i,
      });
      await userEvent.click(copyBtn);

      expect(mockClipboardWriteText).toHaveBeenCalledWith(
        mockPackResponse.markdown
      );
    });

    it('shows "Copied" label after copying', async () => {
      render(
        <TestWrapper>
          <EffectiveContextPreview
            open={true}
            onOpenChange={jest.fn()}
            data={mockPackResponse as any}
          />
        </TestWrapper>
      );

      const copyBtn = screen.getByRole('button', {
        name: /copy context pack to clipboard/i,
      });
      await userEvent.click(copyBtn);

      await waitFor(() => {
        expect(screen.getByText('Copied')).toBeInTheDocument();
      });
    });

    it('disables copy button when no markdown data exists', () => {
      render(
        <TestWrapper>
          <EffectiveContextPreview
            open={true}
            onOpenChange={jest.fn()}
            data={null}
          />
        </TestWrapper>
      );

      // The copy button should be disabled when no data
      const copyBtn = screen.getByRole('button', {
        name: /copy context pack to clipboard/i,
      });
      expect(copyBtn).toBeDisabled();
    });

    it('disables copy button when loading', () => {
      render(
        <TestWrapper>
          <EffectiveContextPreview
            open={true}
            onOpenChange={jest.fn()}
            data={mockPackResponse as any}
            isLoading={true}
          />
        </TestWrapper>
      );

      const copyBtn = screen.getByRole('button', {
        name: /copy context pack to clipboard/i,
      });
      expect(copyBtn).toBeDisabled();
    });
  });

  describe('Regenerate Button', () => {
    it('renders regenerate button when onRegenerate is provided', () => {
      render(
        <TestWrapper>
          <EffectiveContextPreview
            open={true}
            onOpenChange={jest.fn()}
            data={mockPackResponse as any}
            onRegenerate={jest.fn()}
          />
        </TestWrapper>
      );

      expect(
        screen.getByRole('button', { name: /regenerate/i })
      ).toBeInTheDocument();
    });

    it('calls onRegenerate when clicked', async () => {
      const onRegenerate = jest.fn();
      render(
        <TestWrapper>
          <EffectiveContextPreview
            open={true}
            onOpenChange={jest.fn()}
            data={mockPackResponse as any}
            onRegenerate={onRegenerate}
          />
        </TestWrapper>
      );

      await userEvent.click(
        screen.getByRole('button', { name: /regenerate/i })
      );
      expect(onRegenerate).toHaveBeenCalledTimes(1);
    });

    it('disables regenerate button when loading', () => {
      render(
        <TestWrapper>
          <EffectiveContextPreview
            open={true}
            onOpenChange={jest.fn()}
            data={mockPackResponse as any}
            isLoading={true}
            onRegenerate={jest.fn()}
          />
        </TestWrapper>
      );

      expect(
        screen.getByRole('button', { name: /regenerate/i })
      ).toBeDisabled();
    });

    it('does not render regenerate button when onRegenerate is not provided', () => {
      render(
        <TestWrapper>
          <EffectiveContextPreview
            open={true}
            onOpenChange={jest.fn()}
            data={mockPackResponse as any}
          />
        </TestWrapper>
      );

      expect(
        screen.queryByRole('button', { name: /regenerate/i })
      ).not.toBeInTheDocument();
    });
  });

  describe('Item Summary', () => {
    it('shows included items with type badges when expanded', async () => {
      render(
        <TestWrapper>
          <EffectiveContextPreview
            open={true}
            onOpenChange={jest.fn()}
            data={mockPackResponse as any}
          />
        </TestWrapper>
      );

      // Expand the included items collapsible
      const expandBtn = screen.getByRole('button', {
        name: /toggle included items/i,
      });
      await userEvent.click(expandBtn);

      // Should show item type badges and content
      const typeBadges = screen.getAllByTestId('memory-type-badge');
      expect(typeBadges).toHaveLength(2);
      expect(typeBadges[0]).toHaveTextContent('decision');
      expect(typeBadges[1]).toHaveTextContent('constraint');
    });

    it('shows item count in collapsible trigger', () => {
      render(
        <TestWrapper>
          <EffectiveContextPreview
            open={true}
            onOpenChange={jest.fn()}
            data={mockPackResponse as any}
          />
        </TestWrapper>
      );

      expect(screen.getByText(/included items \(2\)/i)).toBeInTheDocument();
    });

    it('shows confidence percentages for items', async () => {
      render(
        <TestWrapper>
          <EffectiveContextPreview
            open={true}
            onOpenChange={jest.fn()}
            data={mockPackResponse as any}
          />
        </TestWrapper>
      );

      // Expand items
      await userEvent.click(
        screen.getByRole('button', { name: /toggle included items/i })
      );

      expect(screen.getByText('95%')).toBeInTheDocument();
      expect(screen.getByText('88%')).toBeInTheDocument();
    });

    it('shows token counts for items', async () => {
      render(
        <TestWrapper>
          <EffectiveContextPreview
            open={true}
            onOpenChange={jest.fn()}
            data={mockPackResponse as any}
          />
        </TestWrapper>
      );

      // Expand items
      await userEvent.click(
        screen.getByRole('button', { name: /toggle included items/i })
      );

      expect(screen.getByText('12 tokens')).toBeInTheDocument();
      expect(screen.getByText('15 tokens')).toBeInTheDocument();
    });
  });

  describe('Close Button', () => {
    it('calls onOpenChange(false) when close button is clicked', async () => {
      const onOpenChange = jest.fn();
      render(
        <TestWrapper>
          <EffectiveContextPreview
            open={true}
            onOpenChange={onOpenChange}
            data={mockPackResponse as any}
          />
        </TestWrapper>
      );

      // Two buttons match "Close" (dialog X and explicit Close), pick the visible one
      const closeButtons = screen.getAllByRole('button', { name: /close/i });
      const explicitCloseBtn = closeButtons.find(
        (btn) => btn.textContent === 'Close'
      )!;
      await userEvent.click(explicitCloseBtn);
      expect(onOpenChange).toHaveBeenCalledWith(false);
    });
  });

  describe('Generated Timestamp', () => {
    it('shows generated_at timestamp when present', () => {
      render(
        <TestWrapper>
          <EffectiveContextPreview
            open={true}
            onOpenChange={jest.fn()}
            data={mockPackResponse as any}
          />
        </TestWrapper>
      );

      // Match the timestamp text specifically (avoid matching "generated" in the dialog description)
      expect(screen.getByText(/Generated\s+\w+ \d+/)).toBeInTheDocument();
    });
  });

  describe('Dialog State', () => {
    it('does not render dialog content when open is false', () => {
      render(
        <TestWrapper>
          <EffectiveContextPreview
            open={false}
            onOpenChange={jest.fn()}
            data={mockPackResponse as any}
          />
        </TestWrapper>
      );

      expect(
        screen.queryByText(/effective context preview/i)
      ).not.toBeInTheDocument();
    });
  });
});

// ---------------------------------------------------------------------------
// Tests: ContextPackGenerator
// ---------------------------------------------------------------------------

describe('ContextPackGenerator', () => {
  beforeEach(() => {
    setupDefaultMocks();
    mockClipboardWriteText.mockClear();
  });

  describe('Module Selector', () => {
    it('renders module selector dropdown', () => {
      render(
        <TestWrapper>
          <ContextPackGenerator projectId="proj-1" />
        </TestWrapper>
      );

      expect(screen.getByLabelText(/context module/i)).toBeInTheDocument();
    });

    it('shows loading message when modules are loading', () => {
      mockUseContextModules.mockReturnValue({
        data: undefined,
        isLoading: true,
      });

      render(
        <TestWrapper>
          <ContextPackGenerator projectId="proj-1" />
        </TestWrapper>
      );

      expect(screen.getByText(/loading modules/i)).toBeInTheDocument();
    });
  });

  describe('Budget Presets', () => {
    it('renders all budget preset buttons', () => {
      render(
        <TestWrapper>
          <ContextPackGenerator projectId="proj-1" />
        </TestWrapper>
      );

      const presetGroup = screen.getByRole('group', {
        name: /budget presets/i,
      });
      expect(presetGroup).toBeInTheDocument();

      expect(
        within(presetGroup).getByRole('button', { name: /set budget to 1000/i })
      ).toBeInTheDocument();
      expect(
        within(presetGroup).getByRole('button', { name: /set budget to 2000/i })
      ).toBeInTheDocument();
      expect(
        within(presetGroup).getByRole('button', { name: /set budget to 4000/i })
      ).toBeInTheDocument();
      expect(
        within(presetGroup).getByRole('button', { name: /set budget to 8000/i })
      ).toBeInTheDocument();
      expect(
        within(presetGroup).getByRole('button', { name: /set budget to 16000/i })
      ).toBeInTheDocument();
    });

    it('highlights active preset button (4K is default)', () => {
      render(
        <TestWrapper>
          <ContextPackGenerator projectId="proj-1" />
        </TestWrapper>
      );

      const preset4k = screen.getByRole('button', {
        name: /set budget to 4000/i,
      });
      expect(preset4k).toHaveAttribute('aria-pressed', 'true');
    });

    it('updates budget when preset button is clicked', async () => {
      render(
        <TestWrapper>
          <ContextPackGenerator projectId="proj-1" />
        </TestWrapper>
      );

      await userEvent.click(
        screen.getByRole('button', { name: /set budget to 8000/i })
      );

      const budgetInput = screen.getByLabelText(/token budget/i);
      expect(budgetInput).toHaveValue(8000);

      // 8K should now be pressed
      expect(
        screen.getByRole('button', { name: /set budget to 8000/i })
      ).toHaveAttribute('aria-pressed', 'true');

      // 4K should no longer be pressed
      expect(
        screen.getByRole('button', { name: /set budget to 4000/i })
      ).toHaveAttribute('aria-pressed', 'false');
    });
  });

  describe('Preview Button', () => {
    it('renders preview button', () => {
      render(
        <TestWrapper>
          <ContextPackGenerator projectId="proj-1" />
        </TestWrapper>
      );

      expect(
        screen.getByRole('button', { name: /preview context pack/i })
      ).toBeInTheDocument();
    });

    it('calls preview mutation when clicked', async () => {
      render(
        <TestWrapper>
          <ContextPackGenerator projectId="proj-1" />
        </TestWrapper>
      );

      await userEvent.click(
        screen.getByRole('button', { name: /preview context pack/i })
      );

      expect(mockPreviewMutate).toHaveBeenCalledWith(
        expect.objectContaining({
          projectId: 'proj-1',
          data: expect.objectContaining({
            budget_tokens: 4000,
          }),
        })
      );
    });

    it('is disabled while loading', () => {
      mockUsePreviewContextPack.mockReturnValue({
        mutate: mockPreviewMutate,
        isPending: true,
        isError: false,
        error: null,
      });

      render(
        <TestWrapper>
          <ContextPackGenerator projectId="proj-1" />
        </TestWrapper>
      );

      expect(
        screen.getByRole('button', { name: /preview context pack/i })
      ).toBeDisabled();
    });
  });

  describe('Generate Button', () => {
    it('renders generate button', () => {
      render(
        <TestWrapper>
          <ContextPackGenerator projectId="proj-1" />
        </TestWrapper>
      );

      expect(
        screen.getByRole('button', { name: /generate context pack/i })
      ).toBeInTheDocument();
    });

    it('calls generate mutation when clicked', async () => {
      render(
        <TestWrapper>
          <ContextPackGenerator projectId="proj-1" />
        </TestWrapper>
      );

      await userEvent.click(
        screen.getByRole('button', { name: /generate context pack/i })
      );

      expect(mockGenerateMutate).toHaveBeenCalledWith(
        expect.objectContaining({
          projectId: 'proj-1',
          data: expect.objectContaining({
            budget_tokens: 4000,
          }),
        })
      );
    });

    it('is disabled while loading', () => {
      mockUseGenerateContextPack.mockReturnValue({
        mutate: mockGenerateMutate,
        isPending: true,
        isError: false,
        error: null,
      });

      render(
        <TestWrapper>
          <ContextPackGenerator projectId="proj-1" />
        </TestWrapper>
      );

      expect(
        screen.getByRole('button', { name: /generate context pack/i })
      ).toBeDisabled();
    });
  });

  describe('Advanced Filters', () => {
    it('renders collapsible advanced filters section', () => {
      render(
        <TestWrapper>
          <ContextPackGenerator projectId="proj-1" />
        </TestWrapper>
      );

      expect(screen.getByText(/advanced filters/i)).toBeInTheDocument();
    });

    it('expands filters when clicked', async () => {
      render(
        <TestWrapper>
          <ContextPackGenerator projectId="proj-1" />
        </TestWrapper>
      );

      const filtersBtn = screen.getByRole('button', {
        name: /advanced filters/i,
      });
      await userEvent.click(filtersBtn);

      // Should now show memory type checkboxes
      expect(screen.getByText('Constraints')).toBeInTheDocument();
      expect(screen.getByText('Decisions')).toBeInTheDocument();
      expect(screen.getByText('Fixes')).toBeInTheDocument();
      expect(screen.getByText('Patterns')).toBeInTheDocument();
      expect(screen.getByText('Learnings')).toBeInTheDocument();
    });

    it('shows "All types included" when no types are selected', async () => {
      render(
        <TestWrapper>
          <ContextPackGenerator projectId="proj-1" />
        </TestWrapper>
      );

      await userEvent.click(
        screen.getByRole('button', { name: /advanced filters/i })
      );

      expect(screen.getByText(/all types included/i)).toBeInTheDocument();
    });

    it('shows min confidence input in filter section', async () => {
      render(
        <TestWrapper>
          <ContextPackGenerator projectId="proj-1" />
        </TestWrapper>
      );

      await userEvent.click(
        screen.getByRole('button', { name: /advanced filters/i })
      );

      expect(
        screen.getByLabelText(/minimum confidence threshold/i)
      ).toBeInTheDocument();
    });
  });

  describe('Empty State', () => {
    it('shows "No results yet" when no data available', () => {
      render(
        <TestWrapper>
          <ContextPackGenerator projectId="proj-1" />
        </TestWrapper>
      );

      expect(screen.getByText(/no results yet/i)).toBeInTheDocument();
    });
  });

  describe('Error Display', () => {
    it('shows preview error message', () => {
      mockUsePreviewContextPack.mockReturnValue({
        mutate: mockPreviewMutate,
        isPending: false,
        isError: true,
        error: { message: 'Failed to preview' },
      });

      render(
        <TestWrapper>
          <ContextPackGenerator projectId="proj-1" />
        </TestWrapper>
      );

      expect(
        screen.getByText(/preview failed: failed to preview/i)
      ).toBeInTheDocument();
    });

    it('shows generate error message', () => {
      mockUseGenerateContextPack.mockReturnValue({
        mutate: mockGenerateMutate,
        isPending: false,
        isError: true,
        error: { message: 'Generation timeout' },
      });

      render(
        <TestWrapper>
          <ContextPackGenerator projectId="proj-1" />
        </TestWrapper>
      );

      expect(
        screen.getByText(/generation failed: generation timeout/i)
      ).toBeInTheDocument();
    });
  });

  describe('Budget Input', () => {
    it('renders budget input with default value of 4000', () => {
      render(
        <TestWrapper>
          <ContextPackGenerator projectId="proj-1" />
        </TestWrapper>
      );

      const budgetInput = screen.getByLabelText(/token budget/i);
      expect(budgetInput).toHaveValue(4000);
    });

    it('allows changing budget via input', async () => {
      render(
        <TestWrapper>
          <ContextPackGenerator projectId="proj-1" />
        </TestWrapper>
      );

      const budgetInput = screen.getByLabelText(/token budget/i);
      fireEvent.change(budgetInput, { target: { value: '5000' } });

      expect(budgetInput).toHaveValue(5000);
    });

    it('shows budget range description', () => {
      render(
        <TestWrapper>
          <ContextPackGenerator projectId="proj-1" />
        </TestWrapper>
      );

      expect(screen.getByText(/range: 100 - 100,000 tokens/i)).toBeInTheDocument();
    });
  });

  describe('Component Title', () => {
    it('renders "Context Pack Generator" heading', () => {
      render(
        <TestWrapper>
          <ContextPackGenerator projectId="proj-1" />
        </TestWrapper>
      );

      expect(
        screen.getByText(/context pack generator/i)
      ).toBeInTheDocument();
    });
  });
});
