/**
 * @jest-environment jsdom
 *
 * Unit tests for Platform Profiles section in CreateProjectDialog (EPP-P3-07)
 *
 * Covers:
 *  1. Toggling a platform ON creates pending state (switch state changes)
 *  2. Customize dialog opens with correct pre-populated platform label
 *  3. Form submission from Customize dialog shows "Customized" indicator
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { CreateProjectDialog } from '@/app/projects/components/create-project-dialog';

// ---------------------------------------------------------------------------
// Mock hooks used by the dialog
// ---------------------------------------------------------------------------
const mockMutateAsync = jest.fn().mockResolvedValue({ id: 'proj-123', name: 'test', path: '/tmp/test' });
const mockToast = jest.fn();

jest.mock('@/hooks', () => ({
  useCreateProject: () => ({
    mutateAsync: mockMutateAsync,
    isPending: false,
  }),
  useToast: () => ({ toast: mockToast }),
}));

// Mock the raw API function used for profile creation
jest.mock('@/lib/api/deployment-profiles', () => ({
  createDeploymentProfile: jest.fn().mockResolvedValue({ id: 'profile-1' }),
}));

// ---------------------------------------------------------------------------
// Mock shadcn Accordion — render children inline for test simplicity
// ---------------------------------------------------------------------------
jest.mock('@/components/ui/accordion', () => {
  const React = require('react');
  return {
    Accordion: ({ children }: { children: React.ReactNode }) =>
      React.createElement('div', { 'data-testid': 'accordion' }, children),
    AccordionItem: ({ children }: { children: React.ReactNode }) =>
      React.createElement('div', { 'data-testid': 'accordion-item' }, children),
    AccordionTrigger: ({
      children,
      onClick,
    }: {
      children: React.ReactNode;
      onClick?: () => void;
    }) =>
      React.createElement(
        'button',
        { type: 'button', 'data-testid': 'accordion-trigger', onClick },
        children
      ),
    AccordionContent: ({ children }: { children: React.ReactNode }) =>
      React.createElement('div', { 'data-testid': 'accordion-content' }, children),
  };
});

// ---------------------------------------------------------------------------
// Mock shadcn Switch — render a real checkbox so fireEvent works
// ---------------------------------------------------------------------------
jest.mock('@/components/ui/switch', () => {
  const React = require('react');
  return {
    Switch: ({
      id,
      checked,
      onCheckedChange,
      disabled,
      'aria-label': ariaLabel,
    }: {
      id?: string;
      checked?: boolean;
      onCheckedChange?: (checked: boolean) => void;
      disabled?: boolean;
      'aria-label'?: string;
    }) =>
      React.createElement('input', {
        id,
        type: 'checkbox',
        role: 'switch',
        checked: !!checked,
        disabled: !!disabled,
        'aria-label': ariaLabel,
        onChange: (e: React.ChangeEvent<HTMLInputElement>) =>
          onCheckedChange?.(e.target.checked),
        'data-testid': `switch-${id}`,
      }),
  };
});

// ---------------------------------------------------------------------------
// Mock shadcn Dialog — render children inline so nested dialogs work
// ---------------------------------------------------------------------------
jest.mock('@/components/ui/dialog', () => {
  const React = require('react');
  return {
    Dialog: ({
      open,
      children,
    }: {
      open?: boolean;
      onOpenChange?: (open: boolean) => void;
      children: React.ReactNode;
    }) => (open ? React.createElement('div', { 'data-testid': 'dialog' }, children) : null),
    DialogContent: ({ children }: { children: React.ReactNode }) =>
      React.createElement('div', { 'data-testid': 'dialog-content' }, children),
    DialogHeader: ({ children }: { children: React.ReactNode }) =>
      React.createElement('div', { 'data-testid': 'dialog-header' }, children),
    DialogTitle: ({ children }: { children: React.ReactNode }) =>
      React.createElement('h2', { 'data-testid': 'dialog-title' }, children),
    DialogDescription: ({ children }: { children: React.ReactNode }) =>
      React.createElement('p', { 'data-testid': 'dialog-description' }, children),
    DialogFooter: ({ children }: { children: React.ReactNode }) =>
      React.createElement('div', { 'data-testid': 'dialog-footer' }, children),
  };
});

// ---------------------------------------------------------------------------
// Mock CreateProfileForm — renders a simple form with a submit button
// ---------------------------------------------------------------------------
jest.mock('@/components/profiles', () => {
  const React = require('react');
  return {
    CreateProfileForm: ({
      onSubmit,
      onCancel,
      platformLock,
      defaultValues,
    }: {
      onSubmit: (data: Record<string, unknown>) => void;
      onCancel?: () => void;
      platformLock?: string;
      defaultValues?: Record<string, unknown>;
    }) =>
      React.createElement(
        'div',
        { 'data-testid': 'create-profile-form', 'data-platform': platformLock },
        React.createElement('span', { 'data-testid': 'form-default-profile-id' }, defaultValues?.profile_id ?? ''),
        React.createElement(
          'button',
          {
            type: 'button',
            'data-testid': 'form-submit',
            onClick: () =>
              onSubmit({
                profile_id: defaultValues?.profile_id ?? `${platformLock}-default`,
                platform: platformLock,
                root_dir: '.test',
                artifact_path_map: {},
                project_config_filenames: [],
                context_path_prefixes: [],
                supported_artifact_types: ['skill'],
              }),
          },
          'Save Profile'
        ),
        onCancel &&
          React.createElement(
            'button',
            { type: 'button', 'data-testid': 'form-cancel', onClick: onCancel },
            'Cancel'
          )
      ),
  };
});

// ---------------------------------------------------------------------------
// Mock shadcn Badge and Button to render as simple elements
// ---------------------------------------------------------------------------
jest.mock('@/components/ui/badge', () => {
  const React = require('react');
  return {
    Badge: ({ children, className }: { children: React.ReactNode; className?: string }) =>
      React.createElement('span', { 'data-testid': 'badge', className }, children),
  };
});

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function renderDialog(overrides: { open?: boolean } = {}) {
  const onOpenChange = jest.fn();
  const onSuccess = jest.fn();
  render(
    <CreateProjectDialog
      open={overrides.open ?? true}
      onOpenChange={onOpenChange}
      onSuccess={onSuccess}
    />
  );
  return { onOpenChange, onSuccess };
}

/** Get the switch for a given platform key */
function getPlatformSwitch(platformKey: string): HTMLInputElement {
  return screen.getByTestId(`switch-platform-toggle-${platformKey}`) as HTMLInputElement;
}

/** Click the Customize button for a given platform label */
function getCustomizeButton(platformLabel: string): HTMLElement {
  return screen.getByRole('button', { name: `Customize ${platformLabel} profile` });
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('CreateProjectDialog — Platform Profiles (EPP-P3)', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  // EPP-P3-01: Accordion renders
  describe('Platform Profiles accordion', () => {
    it('renders the accordion with platform profiles section', () => {
      renderDialog();
      expect(screen.getByTestId('accordion')).toBeInTheDocument();
      // The accordion content should be visible (mocked inline)
      expect(screen.getByTestId('accordion-content')).toBeInTheDocument();
    });

    it('renders platform toggle rows for each platform', () => {
      renderDialog();
      // All 5 platforms from PLATFORM_DEFAULTS should render
      expect(getPlatformSwitch('claude_code')).toBeInTheDocument();
      expect(getPlatformSwitch('codex')).toBeInTheDocument();
      expect(getPlatformSwitch('gemini')).toBeInTheDocument();
      expect(getPlatformSwitch('cursor')).toBeInTheDocument();
      expect(getPlatformSwitch('other')).toBeInTheDocument();
    });

    it('all platform switches start as unchecked', () => {
      renderDialog();
      expect(getPlatformSwitch('claude_code').checked).toBe(false);
      expect(getPlatformSwitch('codex').checked).toBe(false);
      expect(getPlatformSwitch('gemini').checked).toBe(false);
    });
  });

  // EPP-P3-02 + EPP-P3-03: Toggle state management
  describe('Platform toggle creates pending state', () => {
    it('toggling a platform ON changes switch to checked', () => {
      renderDialog();

      const sw = getPlatformSwitch('claude_code');
      expect(sw.checked).toBe(false);

      fireEvent.click(sw);

      expect(sw.checked).toBe(true);
    });

    it('toggling a platform OFF removes it from pending state', () => {
      renderDialog();

      const sw = getPlatformSwitch('claude_code');

      // Toggle ON then OFF
      fireEvent.click(sw);
      expect(sw.checked).toBe(true);

      fireEvent.click(sw);
      expect(sw.checked).toBe(false);
    });

    it('Customize button is disabled when platform toggle is OFF', () => {
      renderDialog();
      const customizeBtn = getCustomizeButton('Claude Code');
      expect(customizeBtn).toBeDisabled();
    });

    it('Customize button is enabled after toggling platform ON', () => {
      renderDialog();

      fireEvent.click(getPlatformSwitch('claude_code'));

      const customizeBtn = getCustomizeButton('Claude Code');
      expect(customizeBtn).not.toBeDisabled();
    });
  });

  // EPP-P3-04: Customize dialog opens
  describe('Customize dialog opens with correct pre-population', () => {
    it('clicking Customize opens nested dialog with CreateProfileForm', async () => {
      renderDialog();

      // Enable platform
      fireEvent.click(getPlatformSwitch('codex'));

      // Open customize dialog
      fireEvent.click(getCustomizeButton('Codex'));

      await waitFor(() => {
        expect(screen.getByTestId('create-profile-form')).toBeInTheDocument();
      });
    });

    it('passes correct platformLock to CreateProfileForm', async () => {
      renderDialog();

      fireEvent.click(getPlatformSwitch('gemini'));
      fireEvent.click(getCustomizeButton('Gemini'));

      await waitFor(() => {
        const form = screen.getByTestId('create-profile-form');
        expect(form).toHaveAttribute('data-platform', 'gemini');
      });
    });

    it('passes pre-populated defaultValues derived from PLATFORM_DEFAULTS', async () => {
      renderDialog();

      fireEvent.click(getPlatformSwitch('cursor'));
      fireEvent.click(getCustomizeButton('Cursor'));

      await waitFor(() => {
        const profileIdSpan = screen.getByTestId('form-default-profile-id');
        expect(profileIdSpan.textContent).toBe('cursor-default');
      });
    });
  });

  // EPP-P3-05: Customized indicator after form save
  describe('Customized indicator appears after saving from Customize dialog', () => {
    it('shows "Customized" badge after saving from Customize dialog', async () => {
      renderDialog();

      // Enable platform
      fireEvent.click(getPlatformSwitch('claude_code'));

      // Open and submit the customize form
      fireEvent.click(getCustomizeButton('Claude Code'));

      await waitFor(() => {
        expect(screen.getByTestId('create-profile-form')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByTestId('form-submit'));

      await waitFor(() => {
        // "Customized" badge should now be visible for this platform
        const badges = screen.getAllByTestId('badge');
        const customizedBadge = badges.find((b) => b.textContent === 'Customized');
        expect(customizedBadge).toBeTruthy();
      });
    });

    it('does not show "Customized" badge for platforms that were not customized', () => {
      renderDialog();

      // Enable without customizing
      fireEvent.click(getPlatformSwitch('codex'));

      const badges = screen.queryAllByTestId('badge');
      const customizedBadge = badges.find((b) => b.textContent === 'Customized');
      expect(customizedBadge).toBeUndefined();
    });

    it('removing Customized badge when platform is toggled OFF', async () => {
      renderDialog();

      // Enable and customize
      fireEvent.click(getPlatformSwitch('claude_code'));
      fireEvent.click(getCustomizeButton('Claude Code'));

      await waitFor(() => {
        expect(screen.getByTestId('form-submit')).toBeInTheDocument();
      });
      fireEvent.click(screen.getByTestId('form-submit'));

      await waitFor(() => {
        const badges = screen.getAllByTestId('badge');
        expect(badges.some((b) => b.textContent === 'Customized')).toBe(true);
      });

      // Toggle OFF should remove Customized state
      fireEvent.click(getPlatformSwitch('claude_code'));

      await waitFor(() => {
        const badges = screen.queryAllByTestId('badge');
        const customizedBadge = badges.find((b) => b.textContent === 'Customized');
        expect(customizedBadge).toBeUndefined();
      });
    });
  });
});
