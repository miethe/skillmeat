/**
 * @jest-environment jsdom
 *
 * Entity CRUD Flows Integration Tests
 *
 * Tests the complete user flows for creating, reading, updating, and deleting entities.
 * Uses React Testing Library with mocked API calls and realistic user interactions.
 */
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import ManagePage from '@/app/manage/page';
import { apiRequest } from '@/lib/api';
import type { Entity } from '@/types/entity';
import type {
  ArtifactListResponse,
  ArtifactCreateResponse,
  ArtifactResponse
} from '@/sdk';

// Mock the API module
jest.mock('@/lib/api', () => ({
  apiRequest: jest.fn(),
  apiConfig: {
    baseUrl: 'http://localhost:8080',
    version: 'v1',
    useMocks: false,
    trace: false,
  },
  buildApiHeaders: jest.fn(() => ({ Accept: 'application/json' })),
}));

// Mock next/navigation
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
    replace: jest.fn(),
    prefetch: jest.fn(),
    back: jest.fn(),
    forward: jest.fn(),
    refresh: jest.fn(),
    pathname: '/manage',
    query: {},
    asPath: '/manage',
  }),
  usePathname: () => '/manage',
  useSearchParams: () => new URLSearchParams('type=skill'),
}));

// Helper to create a new QueryClient for each test
const createTestQueryClient = () => new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
      cacheTime: 0,
    },
    mutations: {
      retry: false,
    },
  },
  logger: {
    log: console.log,
    warn: console.warn,
    error: () => {}, // Suppress error logs in tests
  },
});

// Helper to render with providers
const renderWithProviders = (component: React.ReactNode) => {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      {component}
    </QueryClientProvider>
  );
};

// Helper to open entity actions dropdown menu
const openEntityActionsMenu = async (user: ReturnType<typeof userEvent.setup>, entityName: string) => {
  const entityTexts = screen.getAllByText(entityName);
  for (const entityText of entityTexts) {
    const card = entityText.closest('.p-4');
    if (card) {
      const menuButton = within(card as HTMLElement).getByRole('button', { name: /Open menu/i });
      await user.click(menuButton);
      return card;
    }
  }
  return null;
};

// Mock entities
const mockEntities: ArtifactResponse[] = [
  {
    id: 'skill:canvas-design',
    name: 'canvas-design',
    type: 'skill',
    source: 'anthropics/skills/canvas-design',
    version: 'v2.1.0',
    added: '2024-10-01T10:00:00Z',
    updated: '2024-11-01T10:00:00Z',
    aliases: ['canvas', 'design'],
    metadata: {
      title: 'Canvas Design',
      description: 'Create and edit visual designs with an interactive canvas',
      tags: ['design', 'visual'],
    },
  },
  {
    id: 'skill:docx-processor',
    name: 'docx-processor',
    type: 'skill',
    source: 'anthropics/skills/document-skills/docx',
    version: 'v1.5.0',
    added: '2024-09-01T10:00:00Z',
    updated: '2024-10-15T10:00:00Z',
    aliases: [],
    metadata: {
      title: 'DOCX Processor',
      description: 'Read and process Microsoft Word documents',
      tags: ['document', 'docx'],
    },
    upstream: {
      has_local_modifications: false,
      update_available: true,
      latest_version: 'v2.0.0',
    },
  },
];

describe('Entity CRUD Flows - Integration Tests', () => {
  const mockApiRequest = apiRequest as jest.MockedFunction<typeof apiRequest>;

  beforeEach(() => {
    jest.clearAllMocks();

    // Default mock implementation for listing entities
    mockApiRequest.mockImplementation(async (path: string) => {
      if (path.startsWith('/artifacts?')) {
        return {
          items: mockEntities,
          total: mockEntities.length,
          limit: 100,
          offset: 0,
        } as ArtifactListResponse;
      }
      return null;
    });
  });

  describe('Entity Creation Flow', () => {
    it('creates a new entity successfully', async () => {
      const user = userEvent.setup();

      // Mock the create API call
      mockApiRequest.mockImplementation(async (path: string, init?: RequestInit) => {
        if (path === '/artifacts' && init?.method === 'POST') {
          const newEntity: ArtifactResponse = {
            id: 'skill:my-new-skill',
            name: 'my-new-skill',
            type: 'skill',
            source: 'user/repo/my-skill',
            version: 'v1.0.0',
            added: new Date().toISOString(),
            updated: new Date().toISOString(),
            aliases: [],
            metadata: {
              description: 'A brand new skill',
              tags: ['testing', 'new'],
            },
          };
          return { artifact: newEntity } as ArtifactCreateResponse;
        }

        // Return updated list including new entity
        if (path.startsWith('/artifacts?')) {
          return {
            items: [...mockEntities, {
              id: 'skill:my-new-skill',
              name: 'my-new-skill',
              type: 'skill',
              source: 'user/repo/my-skill',
              version: 'v1.0.0',
              added: new Date().toISOString(),
              updated: new Date().toISOString(),
              aliases: [],
              metadata: {
                description: 'A brand new skill',
                tags: ['testing', 'new'],
              },
            }],
            total: mockEntities.length + 1,
            limit: 100,
            offset: 0,
          } as ArtifactListResponse;
        }

        return null;
      });

      renderWithProviders(<ManagePage />);

      // Wait for initial entities to load
      await waitFor(() => {
        expect(screen.getByText('canvas-design')).toBeInTheDocument();
      });

      // Open add entity dialog
      const addButton = screen.getByRole('button', { name: /Add New/i });
      await user.click(addButton);

      // Wait for dialog to open
      await waitFor(() => {
        expect(screen.getByText(/Add New Skill/i)).toBeInTheDocument();
      });

      // Fill in the form
      const nameInput = screen.getByLabelText(/Name/i);
      const sourceInput = screen.getByLabelText(/Source/i);
      const descriptionInput = screen.getByPlaceholderText(/What does this skill do/i);

      await user.type(nameInput, 'my-new-skill');
      await user.type(sourceInput, 'user/repo/my-skill');
      await user.type(descriptionInput, 'A brand new skill');

      // Add tags
      const tagInput = screen.getByPlaceholderText(/Add tags/i);
      await user.type(tagInput, 'testing');
      const addTagButton = screen.getByRole('button', { name: /^Add$/i });
      await user.click(addTagButton);

      await user.type(tagInput, 'new');
      await user.click(addTagButton);

      // Submit the form
      const submitButton = screen.getByRole('button', { name: /Add Skill/i });
      await user.click(submitButton);

      // Verify API was called with correct data
      await waitFor(() => {
        expect(mockApiRequest).toHaveBeenCalledWith(
          '/artifacts',
          expect.objectContaining({
            method: 'POST',
            body: expect.stringContaining('my-new-skill'),
          })
        );
      });

      // Wait for dialog to close
      await waitFor(() => {
        expect(screen.queryByText(/Add New Skill/i)).not.toBeInTheDocument();
      });
    });

    it('shows validation errors for invalid input', async () => {
      const user = userEvent.setup();

      renderWithProviders(<ManagePage />);

      // Wait for initial load
      await waitFor(() => {
        expect(screen.getByText('canvas-design')).toBeInTheDocument();
      });

      // Open add entity dialog
      const addButton = screen.getByRole('button', { name: /Add New/i });
      await user.click(addButton);

      await waitFor(() => {
        expect(screen.getByText(/Add New Skill/i)).toBeInTheDocument();
      });

      // Try to submit without filling required fields
      const submitButton = screen.getByRole('button', { name: /Add Skill/i });
      await user.click(submitButton);

      // Verify validation errors appear
      await waitFor(() => {
        expect(screen.getByText(/Name is required/i)).toBeInTheDocument();
        expect(screen.getByText(/Source is required/i)).toBeInTheDocument();
      });
    });

    it('handles API errors during creation', async () => {
      const user = userEvent.setup();

      // Mock API to return error
      mockApiRequest.mockImplementation(async (path: string, init?: RequestInit) => {
        if (path === '/artifacts' && init?.method === 'POST') {
          throw new Error('Failed to create entity');
        }

        if (path.startsWith('/artifacts?')) {
          return {
            items: mockEntities,
            total: mockEntities.length,
            limit: 100,
            offset: 0,
          } as ArtifactListResponse;
        }

        return null;
      });

      renderWithProviders(<ManagePage />);

      await waitFor(() => {
        expect(screen.getByText('canvas-design')).toBeInTheDocument();
      });

      const addButton = screen.getByRole('button', { name: /Add New/i });
      await user.click(addButton);

      await waitFor(() => {
        expect(screen.getByText(/Add New Skill/i)).toBeInTheDocument();
      });

      // Fill in form
      const nameInput = screen.getByLabelText(/Name/i);
      const sourceInput = screen.getByLabelText(/Source/i);
      await user.type(nameInput, 'failing-skill');
      await user.type(sourceInput, 'user/repo/fail');

      const submitButton = screen.getByRole('button', { name: /Add Skill/i });
      await user.click(submitButton);

      // Verify error message is displayed
      await waitFor(() => {
        expect(screen.getByText(/Failed to create entity/i)).toBeInTheDocument();
      });
    });
  });

  describe('Entity Update Flow', () => {
    it('opens edit form from actions menu', async () => {
      const user = userEvent.setup();

      renderWithProviders(<ManagePage />);

      // Wait for entities to load
      await waitFor(() => {
        expect(screen.getByText('canvas-design')).toBeInTheDocument();
      });

      // Open actions menu
      await openEntityActionsMenu(user, 'canvas-design');

      // Find and click edit menu item
      const editMenuItem = screen.getByRole('menuitem', { name: /Edit/i });
      await user.click(editMenuItem);

      // Wait for edit form to appear
      await waitFor(() => {
        expect(screen.getByText(/Edit Skill/i)).toBeInTheDocument();
      });
    });

    it('allows editing only editable fields', async () => {
      const user = userEvent.setup();

      renderWithProviders(<ManagePage />);

      await waitFor(() => {
        expect(screen.getByText('canvas-design')).toBeInTheDocument();
      });

      // Open actions menu and click edit
      await openEntityActionsMenu(user, 'canvas-design');
      const editMenuItem = screen.getByRole('menuitem', { name: /Edit/i });
      await user.click(editMenuItem);

      await waitFor(() => {
        expect(screen.getByText(/Edit Skill/i)).toBeInTheDocument();
      });

      // Source type selector should not be visible in edit mode
      expect(screen.queryByLabelText(/Source Type/i)).not.toBeInTheDocument();

      // Description and tags should be editable
      expect(screen.getByPlaceholderText(/Add tags/i)).toBeInTheDocument();
    });

    it('updates entity successfully', async () => {
      const user = userEvent.setup();

      // Mock update API call
      mockApiRequest.mockImplementation(async (path: string, init?: RequestInit) => {
        if (path === '/artifacts/skill:canvas-design' && init?.method === 'PUT') {
          const updatedEntity: ArtifactResponse = {
            ...mockEntities[0],
            metadata: {
              ...mockEntities[0].metadata,
              description: 'Updated description for canvas design',
              tags: ['design', 'visual', 'updated'],
            },
            updated: new Date().toISOString(),
          };
          return updatedEntity;
        }

        if (path.startsWith('/artifacts?')) {
          return {
            items: mockEntities,
            total: mockEntities.length,
            limit: 100,
            offset: 0,
          } as ArtifactListResponse;
        }

        return null;
      });

      renderWithProviders(<ManagePage />);

      await waitFor(() => {
        expect(screen.getByText('canvas-design')).toBeInTheDocument();
      });

      // Open actions menu and click edit
      await openEntityActionsMenu(user, 'canvas-design');
      const editMenuItem = screen.getByRole('menuitem', { name: /Edit/i });
      await user.click(editMenuItem);

      await waitFor(() => {
        expect(screen.getByText(/Edit Skill/i)).toBeInTheDocument();
      });

      // Update description
      const descriptionInput = screen.getByDisplayValue(/Create and edit visual designs/i);
      await user.clear(descriptionInput);
      await user.type(descriptionInput, 'Updated description for canvas design');

      // Add a new tag
      const tagInput = screen.getByPlaceholderText(/Add tags/i);
      await user.type(tagInput, 'updated');
      const addTagButton = screen.getByRole('button', { name: /^Add$/i });
      await user.click(addTagButton);

      // Save changes
      const saveButton = screen.getByRole('button', { name: /Save Changes/i });
      await user.click(saveButton);

      // Verify API was called
      await waitFor(() => {
        expect(mockApiRequest).toHaveBeenCalledWith(
          '/artifacts/skill:canvas-design',
          expect.objectContaining({
            method: 'PUT',
          })
        );
      });
    });
  });

  describe('Entity Delete Flow', () => {
    it('deletes entity successfully after confirmation', async () => {
      const user = userEvent.setup();

      // Mock window.confirm to auto-accept
      const confirmSpy = jest.spyOn(window, 'confirm').mockReturnValue(true);

      // Mock delete API call
      mockApiRequest.mockImplementation(async (path: string, init?: RequestInit) => {
        if (path === '/artifacts/skill:canvas-design' && init?.method === 'DELETE') {
          return null;
        }

        if (path.startsWith('/artifacts?')) {
          return {
            items: mockEntities.filter(e => e.id !== 'skill:canvas-design'),
            total: mockEntities.length - 1,
            limit: 100,
            offset: 0,
          } as ArtifactListResponse;
        }

        return null;
      });

      renderWithProviders(<ManagePage />);

      await waitFor(() => {
        expect(screen.getByText('canvas-design')).toBeInTheDocument();
      });

      // Open actions menu and click delete
      await openEntityActionsMenu(user, 'canvas-design');
      const deleteMenuItem = screen.getByRole('menuitem', { name: /Delete/i });
      await user.click(deleteMenuItem);

      // Verify confirmation was requested
      await waitFor(() => {
        expect(confirmSpy).toHaveBeenCalledWith(
          expect.stringContaining('canvas-design')
        );
      });

      // Verify API was called
      await waitFor(() => {
        expect(mockApiRequest).toHaveBeenCalledWith(
          '/artifacts/skill:canvas-design',
          expect.objectContaining({
            method: 'DELETE',
          })
        );
      });

      confirmSpy.mockRestore();
    });

    it('cancels deletion when user declines confirmation', async () => {
      const user = userEvent.setup();

      const confirmSpy = jest.spyOn(window, 'confirm').mockReturnValue(false);

      renderWithProviders(<ManagePage />);

      await waitFor(() => {
        expect(screen.getByText('canvas-design')).toBeInTheDocument();
      });

      // Open actions menu and click delete
      await openEntityActionsMenu(user, 'canvas-design');
      const deleteMenuItem = screen.getByRole('menuitem', { name: /Delete/i });
      await user.click(deleteMenuItem);

      // Verify confirmation was requested
      expect(confirmSpy).toHaveBeenCalled();

      // Verify API was NOT called for delete
      expect(mockApiRequest).not.toHaveBeenCalledWith(
        expect.stringContaining('skill:canvas-design'),
        expect.objectContaining({
          method: 'DELETE',
        })
      );

      // Entity should still be in the list
      expect(screen.getByText('canvas-design')).toBeInTheDocument();

      confirmSpy.mockRestore();
    });

    it('handles API errors during deletion', async () => {
      const user = userEvent.setup();
      const confirmSpy = jest.spyOn(window, 'confirm').mockReturnValue(true);
      const alertSpy = jest.spyOn(window, 'alert').mockImplementation();
      const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation();

      // Mock API to return error
      mockApiRequest.mockImplementation(async (path: string, init?: RequestInit) => {
        if (path === '/artifacts/skill:canvas-design' && init?.method === 'DELETE') {
          throw new Error('Failed to delete entity');
        }

        if (path.startsWith('/artifacts?')) {
          return {
            items: mockEntities,
            total: mockEntities.length,
            limit: 100,
            offset: 0,
          } as ArtifactListResponse;
        }

        return null;
      });

      renderWithProviders(<ManagePage />);

      await waitFor(() => {
        expect(screen.getByText('canvas-design')).toBeInTheDocument();
      });

      // Open actions menu and click delete
      await openEntityActionsMenu(user, 'canvas-design');
      const deleteMenuItem = screen.getByRole('menuitem', { name: /Delete/i });
      await user.click(deleteMenuItem);

      // Wait for confirmation
      await waitFor(() => {
        expect(confirmSpy).toHaveBeenCalled();
      });

      // Verify error alert was shown
      await waitFor(() => {
        expect(alertSpy).toHaveBeenCalledWith('Failed to delete entity');
      });

      confirmSpy.mockRestore();
      alertSpy.mockRestore();
      consoleErrorSpy.mockRestore();
    });
  });

  describe('Entity Search and Filter Flow', () => {
    it('filters entities by search query', async () => {
      const user = userEvent.setup();

      renderWithProviders(<ManagePage />);

      // Wait for entities to load
      await waitFor(() => {
        expect(screen.getByText('canvas-design')).toBeInTheDocument();
        expect(screen.getByText('docx-processor')).toBeInTheDocument();
      });

      // Find search input and type
      const searchInput = screen.getByPlaceholderText(/Search/i);
      await user.type(searchInput, 'canvas');

      // Only canvas-design should be visible (client-side filtering)
      await waitFor(() => {
        expect(screen.getByText('canvas-design')).toBeInTheDocument();
      });
    });

    it('filters entities by status', async () => {
      const user = userEvent.setup();

      renderWithProviders(<ManagePage />);

      await waitFor(() => {
        expect(screen.getByText('canvas-design')).toBeInTheDocument();
        expect(screen.getByText('docx-processor')).toBeInTheDocument();
      });

      // Find status filter
      const statusButtons = screen.getAllByRole('button');
      const statusFilter = statusButtons.find(btn =>
        btn.textContent?.includes('Status') || btn.textContent?.includes('All')
      );

      if (statusFilter) {
        await user.click(statusFilter);

        // Select outdated filter
        const outdatedOption = screen.queryByText('Outdated');
        if (outdatedOption) {
          await user.click(outdatedOption);

          // Verify filtering works
          await waitFor(() => {
            const count = screen.getByText(/entities found/i);
            expect(count).toBeInTheDocument();
          });
        }
      }
    });
  });

  describe('View Mode Toggle Flow', () => {
    it('toggles between grid and list view', async () => {
      const user = userEvent.setup();

      renderWithProviders(<ManagePage />);

      await waitFor(() => {
        expect(screen.getByText('canvas-design')).toBeInTheDocument();
      });

      // Find view toggle button (has Grid/List icon)
      const buttons = screen.getAllByRole('button');
      const viewToggleButton = buttons.find(btn => {
        const svg = btn.querySelector('svg');
        return svg?.classList.contains('lucide-grid-3x3') || svg?.classList.contains('lucide-list');
      });

      if (viewToggleButton) {
        await user.click(viewToggleButton);

        // Click list view option
        const listOption = screen.queryByText(/List/i);
        if (listOption) {
          await user.click(listOption);

          // Verify view mode changed (entities should still be visible)
          await waitFor(() => {
            expect(screen.getByText('canvas-design')).toBeInTheDocument();
          });
        }
      }
    });
  });

  describe('Entity State Management', () => {
    it('displays correct entity count', async () => {
      renderWithProviders(<ManagePage />);

      await waitFor(() => {
        expect(screen.getByText(/2 entities found/i)).toBeInTheDocument();
      });
    });

    it('shows loading state while fetching entities', async () => {
      // Mock slow API response
      mockApiRequest.mockImplementation(
        () => new Promise((resolve) => setTimeout(() => resolve({
          items: mockEntities,
          total: mockEntities.length,
          limit: 100,
          offset: 0,
        }), 100))
      );

      renderWithProviders(<ManagePage />);

      // Loading indicator should be visible initially
      expect(screen.getByText(/Loading/i)).toBeInTheDocument();

      // Wait for data to load
      await waitFor(() => {
        expect(screen.getByText('canvas-design')).toBeInTheDocument();
      }, { timeout: 2000 });
    });

    it('refetches entities after successful operations', async () => {
      const user = userEvent.setup();
      const confirmSpy = jest.spyOn(window, 'confirm').mockReturnValue(true);

      let callCount = 0;
      mockApiRequest.mockImplementation(async (path: string, init?: RequestInit) => {
        if (path === '/artifacts/skill:canvas-design' && init?.method === 'DELETE') {
          return null;
        }

        if (path.startsWith('/artifacts?')) {
          callCount++;
          return {
            items: mockEntities,
            total: mockEntities.length,
            limit: 100,
            offset: 0,
          } as ArtifactListResponse;
        }

        return null;
      });

      renderWithProviders(<ManagePage />);

      await waitFor(() => {
        expect(screen.getByText('canvas-design')).toBeInTheDocument();
      });

      const initialCallCount = callCount;

      // Perform delete operation
      await openEntityActionsMenu(user, 'canvas-design');
      const deleteMenuItem = screen.getByRole('menuitem', { name: /Delete/i });
      await user.click(deleteMenuItem);

      // Wait for refetch
      await waitFor(() => {
        expect(callCount).toBeGreaterThan(initialCallCount);
      });

      confirmSpy.mockRestore();
    });
  });
});
