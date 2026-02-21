/**
 * @jest-environment jsdom
 */
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { EntityForm } from '@/components/entity/entity-form';
import type { Entity } from '@/types/entity';

// Mock the useEntityLifecycle hook
jest.mock('@/hooks/useEntityLifecycle', () => ({
  useEntityLifecycle: () => ({
    createEntity: jest.fn().mockResolvedValue({}),
    updateEntity: jest.fn().mockResolvedValue({}),
  }),
}));

const mockSkillEntity: Entity = {
  id: 'skill:test',
  uuid: '00000000000000000000000000000001',
  name: 'test-skill',
  type: 'skill',
  scope: 'user',
  source: 'github:user/repo/skill',
  syncStatus: 'synced',
  tags: ['testing', 'example'],
  description: 'A test skill',
  createdAt: '2024-01-01T00:00:00Z',
  updatedAt: '2024-01-01T00:00:00Z',
};

describe('EntityForm', () => {
  describe('Create Mode', () => {
    it('renders form fields for skill creation', () => {
      render(<EntityForm mode="create" entityType="skill" />);

      expect(screen.getByLabelText(/Name/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Source Type/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Source/i)).toBeInTheDocument();
    });

    it('displays source type radio buttons', () => {
      render(<EntityForm mode="create" entityType="skill" />);

      const githubRadio = screen.getByRole('radio', { name: /GitHub/i });
      const localRadio = screen.getByRole('radio', { name: /Local/i });

      expect(githubRadio).toBeInTheDocument();
      expect(localRadio).toBeInTheDocument();
      expect(githubRadio).toBeChecked();
    });

    it('changes placeholder based on source type selection', () => {
      render(<EntityForm mode="create" entityType="skill" />);

      const sourceInput = screen.getByLabelText(/Source/i);
      expect(sourceInput).toHaveAttribute('placeholder', 'owner/repo/path[@version]');

      const localRadio = screen.getByRole('radio', { name: /Local/i });
      fireEvent.click(localRadio);

      expect(sourceInput).toHaveAttribute('placeholder', '/absolute/path/to/artifact');
    });

    it('validates required fields on submit', async () => {
      render(<EntityForm mode="create" entityType="skill" />);

      const submitButton = screen.getByRole('button', { name: /Add Skill/i });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/Name is required/i)).toBeInTheDocument();
      });
    });

    it('validates name field pattern', async () => {
      const user = userEvent.setup();
      render(<EntityForm mode="create" entityType="skill" />);

      const nameInput = screen.getByLabelText(/Name/i);
      await user.type(nameInput, 'invalid name!');

      const submitButton = screen.getByRole('button', { name: /Add Skill/i });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(
          screen.getByText(
            /Name must contain only alphanumeric characters, hyphens, and underscores/i
          )
        ).toBeInTheDocument();
      });
    });

    it('allows adding and removing tags', async () => {
      const user = userEvent.setup();
      render(<EntityForm mode="create" entityType="skill" />);

      const tagInput = screen.getByPlaceholderText(/Add tags/i);
      await user.type(tagInput, 'test-tag');

      const addButton = screen.getByRole('button', { name: /Add/i });
      fireEvent.click(addButton);

      expect(screen.getByText('test-tag')).toBeInTheDocument();

      // Remove the tag
      const removeButton = screen.getByRole('button', {
        name: '',
      });
      fireEvent.click(removeButton);

      await waitFor(() => {
        expect(screen.queryByText('test-tag')).not.toBeInTheDocument();
      });
    });

    it('adds tag on Enter key press', async () => {
      const user = userEvent.setup();
      render(<EntityForm mode="create" entityType="skill" />);

      const tagInput = screen.getByPlaceholderText(/Add tags/i);
      await user.type(tagInput, 'enter-tag{Enter}');

      expect(screen.getByText('enter-tag')).toBeInTheDocument();
    });

    it('prevents duplicate tags', async () => {
      const user = userEvent.setup();
      render(<EntityForm mode="create" entityType="skill" />);

      const tagInput = screen.getByPlaceholderText(/Add tags/i);
      const addButton = screen.getByRole('button', { name: /Add/i });

      await user.type(tagInput, 'duplicate');
      fireEvent.click(addButton);

      await user.type(tagInput, 'duplicate');
      fireEvent.click(addButton);

      // Should only show one instance
      const tags = screen.getAllByText('duplicate');
      expect(tags).toHaveLength(1);
    });

    it('displays cancel button when onCancel provided', () => {
      const handleCancel = jest.fn();
      render(<EntityForm mode="create" entityType="skill" onCancel={handleCancel} />);

      const cancelButton = screen.getByRole('button', { name: /Cancel/i });
      expect(cancelButton).toBeInTheDocument();

      fireEvent.click(cancelButton);
      expect(handleCancel).toHaveBeenCalled();
    });

    it('shows loading state during submission', async () => {
      const { useEntityLifecycle } = require('@/hooks/useEntityLifecycle');
      useEntityLifecycle.mockImplementation(() => ({
        createEntity: jest
          .fn()
          .mockImplementation(() => new Promise((resolve) => setTimeout(resolve, 100))),
        updateEntity: jest.fn(),
      }));

      const user = userEvent.setup();
      render(<EntityForm mode="create" entityType="skill" />);

      const nameInput = screen.getByLabelText(/Name/i);
      const sourceInput = screen.getByLabelText(/Source/i);
      await user.type(nameInput, 'test-skill');
      await user.type(sourceInput, 'user/repo/skill');

      const submitButton = screen.getByRole('button', { name: /Add Skill/i });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/Adding.../i)).toBeInTheDocument();
      });
    });

    it('shows error message on submission failure', async () => {
      const { useEntityLifecycle } = require('@/hooks/useEntityLifecycle');
      useEntityLifecycle.mockImplementation(() => ({
        createEntity: jest.fn().mockRejectedValue(new Error('API Error')),
        updateEntity: jest.fn(),
      }));

      const user = userEvent.setup();
      render(<EntityForm mode="create" entityType="skill" />);

      const nameInput = screen.getByLabelText(/Name/i);
      const sourceInput = screen.getByLabelText(/Source/i);
      await user.type(nameInput, 'test-skill');
      await user.type(sourceInput, 'user/repo/skill');

      const submitButton = screen.getByRole('button', { name: /Add Skill/i });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText('API Error')).toBeInTheDocument();
      });
    });
  });

  describe('Edit Mode', () => {
    it('renders form with entity data', () => {
      render(<EntityForm mode="edit" entity={mockSkillEntity} />);

      expect(screen.getByText(/Edit Skill/i)).toBeInTheDocument();
      expect(screen.getByDisplayValue('A test skill')).toBeInTheDocument();
    });

    it('shows existing tags', () => {
      render(<EntityForm mode="edit" entity={mockSkillEntity} />);

      expect(screen.getByText('testing')).toBeInTheDocument();
      expect(screen.getByText('example')).toBeInTheDocument();
    });

    it('disables name field in edit mode', () => {
      render(<EntityForm mode="edit" entity={mockSkillEntity} />);

      const nameInput = screen.queryByDisplayValue('test-skill');
      expect(nameInput).toBeDisabled();
    });

    it('disables source field in edit mode', () => {
      render(<EntityForm mode="edit" entity={mockSkillEntity} />);

      // Source field should not be visible in edit mode
      expect(screen.queryByLabelText(/Source Type/i)).not.toBeInTheDocument();
    });

    it('allows editing description and tags', async () => {
      const user = userEvent.setup();
      render(<EntityForm mode="edit" entity={mockSkillEntity} />);

      const descriptionInput = screen.getByDisplayValue('A test skill');
      await user.clear(descriptionInput);
      await user.type(descriptionInput, 'Updated description');

      expect(screen.getByDisplayValue('Updated description')).toBeInTheDocument();
    });

    it('shows Save Changes button in edit mode', () => {
      render(<EntityForm mode="edit" entity={mockSkillEntity} />);

      expect(screen.getByRole('button', { name: /Save Changes/i })).toBeInTheDocument();
    });
  });

  describe('Invalid State', () => {
    it('shows invalid entity type message when type is missing', () => {
      render(<EntityForm mode="create" />);

      expect(screen.getByText('Invalid entity type')).toBeInTheDocument();
    });
  });

  describe('Field Rendering', () => {
    it('renders text input fields', () => {
      render(<EntityForm mode="create" entityType="skill" />);

      expect(screen.getByLabelText(/Name/i)).toHaveAttribute('type', 'text');
    });

    it('renders textarea for description', () => {
      render(<EntityForm mode="create" entityType="skill" />);

      const descriptionField = screen.queryByPlaceholderText(/Brief description/i);
      expect(descriptionField).toBeInTheDocument();
    });

    it('shows required field indicator', () => {
      render(<EntityForm mode="create" entityType="skill" />);

      // Name should have required indicator (*)
      const nameLabel = screen.getByText(/Name/);
      expect(nameLabel.parentElement).toHaveTextContent('*');
    });
  });
});
