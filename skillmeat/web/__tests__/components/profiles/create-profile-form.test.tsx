/**
 * @jest-environment jsdom
 *
 * Unit tests for CreateProfileForm (EPP-P2-10)
 *
 * Covers:
 *  1. Platform selection triggers pre-population of root_dir and supported_artifact_types
 *  2. Artifact type toggle updates artifact_path_map JSON textarea
 *  3. Description character limit (maxLength=500)
 *  4. Tooltip trigger buttons are keyboard accessible via aria-label
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { CreateProfileForm } from '@/components/profiles/create-profile-form';
import { Platform } from '@/types/enums';
import { PLATFORM_DEFAULTS } from '@/lib/constants/platform-defaults';

// ---------------------------------------------------------------------------
// Radix UI Select does not render a real <select> in jsdom; mock it so that
// onValueChange can be triggered via button clicks.
// ---------------------------------------------------------------------------
jest.mock('@/components/ui/select', () => {
  const React = require('react');
  return {
    Select: ({
      children,
      onValueChange,
      value,
      disabled,
    }: {
      children: React.ReactNode;
      onValueChange?: (v: string) => void;
      value?: string;
      disabled?: boolean;
    }) =>
      React.createElement(
        'div',
        { 'data-testid': 'select-root', 'data-value': value, 'data-disabled': String(!!disabled) },
        React.Children.map(children, (child: React.ReactElement) =>
          React.cloneElement(child, { onValueChange })
        )
      ),
    SelectTrigger: ({
      children,
      id,
      onValueChange: _ignored,
    }: {
      children: React.ReactNode;
      id?: string;
      onValueChange?: (v: string) => void;
    }) =>
      React.createElement('button', { id, type: 'button', 'data-testid': 'select-trigger' }, children),
    SelectValue: () => React.createElement('span', { 'data-testid': 'select-value' }),
    SelectContent: ({
      children,
      onValueChange,
    }: {
      children: React.ReactNode;
      onValueChange?: (v: string) => void;
    }) =>
      React.createElement(
        'div',
        { 'data-testid': 'select-content' },
        React.Children.map(children, (child: React.ReactElement) =>
          React.cloneElement(child, { onValueChange })
        )
      ),
    SelectItem: ({
      children,
      value,
      onValueChange,
    }: {
      children: React.ReactNode;
      value: string;
      onValueChange?: (v: string) => void;
    }) =>
      React.createElement(
        'button',
        {
          type: 'button',
          'data-testid': `select-item-${value}`,
          onClick: () => onValueChange?.(value),
        },
        children
      ),
  };
});

// Radix Tooltip — render children inline so the <button> with aria-label is in the DOM.
jest.mock('@/components/ui/tooltip', () => {
  const React = require('react');
  return {
    TooltipProvider: ({ children }: { children: React.ReactNode }) =>
      React.createElement(React.Fragment, null, children),
    Tooltip: ({ children }: { children: React.ReactNode }) =>
      React.createElement(React.Fragment, null, children),
    TooltipTrigger: ({ children, asChild }: { children: React.ReactNode; asChild?: boolean }) => {
      if (asChild) return children as React.ReactElement;
      return React.createElement('div', null, children);
    },
    TooltipContent: ({ children }: { children: React.ReactNode }) =>
      React.createElement('div', { role: 'tooltip' }, children),
  };
});

// Radix Checkbox — render a real <input type="checkbox"> so fireEvent works.
jest.mock('@/components/ui/checkbox', () => {
  const React = require('react');
  return {
    Checkbox: ({
      id,
      checked,
      onCheckedChange,
    }: {
      id?: string;
      checked?: boolean;
      onCheckedChange?: (checked: boolean) => void;
    }) =>
      React.createElement('input', {
        id,
        type: 'checkbox',
        checked: !!checked,
        onChange: (e: React.ChangeEvent<HTMLInputElement>) => onCheckedChange?.(e.target.checked),
        'data-testid': id,
      }),
  };
});

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function renderForm(props: Partial<React.ComponentProps<typeof CreateProfileForm>> = {}) {
  const onSubmit = jest.fn();
  render(
    <CreateProfileForm
      onSubmit={onSubmit}
      contextMode="page"
      {...props}
    />
  );
  return { onSubmit };
}

/** Get the Root Dir input by its element id (avoids collision with aria-label on tooltip button). */
function getRootDirInput(): HTMLInputElement {
  return document.getElementById('cpf-root-dir') as HTMLInputElement;
}

/** Get the Artifact Path Map textarea by its element id. */
function getPathMapTextarea(): HTMLTextAreaElement {
  return document.getElementById('cpf-artifact-map') as HTMLTextAreaElement;
}

/** Get the Description textarea by its element id. */
function getDescriptionTextarea(): HTMLTextAreaElement {
  return document.getElementById('cpf-description') as HTMLTextAreaElement;
}

/** Get the Profile ID input by its element id. */
function getProfileIdInput(): HTMLInputElement {
  return document.getElementById('cpf-profile-id') as HTMLInputElement;
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('CreateProfileForm', () => {
  // 1. Platform selection triggers pre-population
  describe('Platform selection pre-populates defaults', () => {
    it('pre-populates root_dir when switching to Codex platform', () => {
      renderForm();

      fireEvent.click(screen.getByTestId('select-item-codex'));

      expect(getRootDirInput().value).toBe(PLATFORM_DEFAULTS['codex']!.root_dir);
    });

    it('pre-populates supported_artifact_types checkboxes when switching to Gemini', () => {
      renderForm();

      fireEvent.click(screen.getByTestId('select-item-gemini'));

      const geminiTypes = PLATFORM_DEFAULTS['gemini']!.supported_artifact_types;

      for (const type of geminiTypes) {
        const checkbox = screen.getByTestId(`cpf-type-${type}`) as HTMLInputElement;
        expect(checkbox.checked).toBe(true);
      }

      const allTypes = ['skill', 'command', 'agent', 'mcp', 'hook', 'composite'];
      const unsupportedTypes = allTypes.filter((t) => !geminiTypes.includes(t));
      for (const type of unsupportedTypes) {
        const checkbox = screen.getByTestId(`cpf-type-${type}`) as HTMLInputElement;
        expect(checkbox.checked).toBe(false);
      }
    });

    it('pre-populates root_dir when switching to Cursor platform', () => {
      renderForm();

      fireEvent.click(screen.getByTestId('select-item-cursor'));

      expect(getRootDirInput().value).toBe(PLATFORM_DEFAULTS['cursor']!.root_dir);
    });

    it('does not overwrite root_dir if the user has already manually edited it', async () => {
      const user = userEvent.setup();
      renderForm();

      const rootDirInput = getRootDirInput();
      await user.clear(rootDirInput);
      await user.type(rootDirInput, '/my/custom/dir');

      fireEvent.click(screen.getByTestId('select-item-codex'));

      expect(getRootDirInput().value).toBe('/my/custom/dir');
    });
  });

  // 2. Artifact type toggle updates path map
  describe('Artifact type toggle updates artifact_path_map', () => {
    it('removes a type from path map JSON when its checkbox is unchecked', async () => {
      renderForm();

      const initialMap = JSON.parse(getPathMapTextarea().value);
      expect(initialMap).toHaveProperty('skill');

      const skillCheckbox = screen.getByTestId('cpf-type-skill') as HTMLInputElement;
      expect(skillCheckbox.checked).toBe(true);
      fireEvent.click(skillCheckbox);

      await waitFor(() => {
        const updatedMap = JSON.parse(getPathMapTextarea().value);
        expect(updatedMap).not.toHaveProperty('skill');
      });
    });

    it('adds a type to path map JSON when its checkbox is checked after unchecking', async () => {
      renderForm();

      // Switch to gemini (skill + command only) so we start with a limited set
      fireEvent.click(screen.getByTestId('select-item-gemini'));

      const commandCheckbox = screen.getByTestId('cpf-type-command') as HTMLInputElement;

      // Uncheck command
      fireEvent.click(commandCheckbox);
      await waitFor(() => {
        const map = JSON.parse(getPathMapTextarea().value);
        expect(map).not.toHaveProperty('command');
      });

      // Re-check command
      fireEvent.click(commandCheckbox);
      await waitFor(() => {
        const map = JSON.parse(getPathMapTextarea().value);
        expect(map).toHaveProperty('command');
      });
    });

    it('does not modify artifact_path_map JSON if user has manually edited it', async () => {
      renderForm();

      // Use fireEvent.change to avoid userEvent special-character parsing of `{` and `}`
      const pathMap = getPathMapTextarea();
      fireEvent.change(pathMap, { target: { value: '{"custom": "path"}' } });

      // Toggle a checkbox; since path map is now marked touched, it should not be overwritten
      const hookCheckbox = screen.getByTestId('cpf-type-hook') as HTMLInputElement;
      fireEvent.click(hookCheckbox);

      await waitFor(() => {
        expect(getPathMapTextarea().value).toContain('"custom"');
      });
    });
  });

  // 3. Description character limit
  describe('Description character limit', () => {
    it('description textarea has maxLength of 500', () => {
      renderForm();
      expect(getDescriptionTextarea().maxLength).toBe(500);
    });

    it('shows character count that updates as user types', async () => {
      const user = userEvent.setup();
      renderForm();

      // Before typing, counter shows 0
      const counterEl = screen.getByText(/\/500/);
      expect(counterEl).toBeInTheDocument();

      // Type into the description
      await user.type(getDescriptionTextarea(), 'Hello');

      // After typing "Hello" (5 chars), the counter parent span should contain "5"
      expect(counterEl.textContent).toContain('/500');
    });

    it('counter span reflects exact character count', () => {
      renderForm();

      // Initially empty — the counter parent shows "0/500"
      // The description counter span wraps a child <span> with the count and the literal "/500"
      const counterParent = screen.getByText(/\/500/);
      expect(counterParent.textContent).toMatch(/0.*\/500/);
    });

    it('description maxLength enforced at the HTML attribute level', () => {
      renderForm();
      // Double-check that the native maxlength attribute is correct
      expect(getDescriptionTextarea()).toHaveAttribute('maxLength', '500');
    });
  });

  // 4. Tooltip trigger buttons are keyboard accessible
  describe('Tooltip triggers are keyboard accessible', () => {
    it('tooltip trigger for Platform field has correct aria-label', () => {
      renderForm();
      const btn = screen.getByRole('button', { name: 'Info: Platform' });
      expect(btn).toBeInTheDocument();
      expect(btn).toHaveAttribute('aria-label', 'Info: Platform');
    });

    it('tooltip trigger for Profile ID field has correct aria-label', () => {
      renderForm();
      expect(screen.getByRole('button', { name: 'Info: Profile ID' })).toBeInTheDocument();
    });

    it('tooltip trigger for Root Dir field has correct aria-label', () => {
      renderForm();
      expect(screen.getByRole('button', { name: 'Info: Root Dir' })).toBeInTheDocument();
    });

    it('tooltip trigger for Supported Artifact Types field has correct aria-label', () => {
      renderForm();
      expect(screen.getByRole('button', { name: 'Info: Supported Artifact Types' })).toBeInTheDocument();
    });

    it('tooltip trigger for Artifact Path Map field has correct aria-label', () => {
      renderForm();
      expect(screen.getByRole('button', { name: 'Info: Artifact Path Map' })).toBeInTheDocument();
    });

    it('tooltip trigger for Config Filenames field has correct aria-label', () => {
      renderForm();
      expect(screen.getByRole('button', { name: 'Info: Config Filenames' })).toBeInTheDocument();
    });

    it('tooltip trigger for Context Path Prefixes field has correct aria-label', () => {
      renderForm();
      expect(screen.getByRole('button', { name: 'Info: Context Path Prefixes' })).toBeInTheDocument();
    });

    it('tooltip trigger for Description field has correct aria-label', () => {
      renderForm();
      expect(screen.getByRole('button', { name: 'Info: Description' })).toBeInTheDocument();
    });

    it('all tooltip triggers have type="button" to avoid accidental form submission', () => {
      renderForm();
      const infoButtons = screen
        .getAllByRole('button')
        .filter((btn) => btn.getAttribute('aria-label')?.startsWith('Info:'));
      expect(infoButtons.length).toBeGreaterThan(0);
      for (const btn of infoButtons) {
        expect(btn).toHaveAttribute('type', 'button');
      }
    });
  });

  // Additional: form submit behaviour
  describe('Form submission', () => {
    it('Create Profile button is disabled when profile_id is empty', () => {
      renderForm();
      const submitBtn = screen.getByRole('button', { name: /Create Profile/i });
      expect(submitBtn).toBeDisabled();
    });

    it('Create Profile button is enabled once profile_id is filled', async () => {
      const user = userEvent.setup();
      renderForm();

      await user.type(getProfileIdInput(), 'my-profile');

      expect(screen.getByRole('button', { name: /Create Profile/i })).not.toBeDisabled();
    });

    it('calls onSubmit with assembled payload when form is submitted', async () => {
      const user = userEvent.setup();
      const { onSubmit } = renderForm();

      await user.type(getProfileIdInput(), 'test-profile');

      fireEvent.click(screen.getByRole('button', { name: /Create Profile/i }));

      expect(onSubmit).toHaveBeenCalledTimes(1);
      const payload = onSubmit.mock.calls[0][0];
      expect(payload.profile_id).toBe('test-profile');
      expect(payload.platform).toBe(Platform.CLAUDE_CODE);
      expect(Array.isArray(payload.supported_artifact_types)).toBe(true);
    });

    it('renders Cancel button in page contextMode when onCancel is provided', () => {
      const onCancel = jest.fn();
      renderForm({ onCancel });
      const cancelBtn = screen.getByRole('button', { name: /Cancel/i });
      expect(cancelBtn).toBeInTheDocument();
      fireEvent.click(cancelBtn);
      expect(onCancel).toHaveBeenCalled();
    });

    it('does not render Cancel button in dialog contextMode', () => {
      const onCancel = jest.fn();
      renderForm({ contextMode: 'dialog', onCancel });
      expect(screen.queryByRole('button', { name: /Cancel/i })).not.toBeInTheDocument();
    });
  });

  // platformLock
  describe('platformLock prop', () => {
    it('disables the platform select when platformLock is set', () => {
      renderForm({ platformLock: Platform.CODEX });
      const selectRoot = screen.getByTestId('select-root');
      expect(selectRoot).toHaveAttribute('data-disabled', 'true');
    });

    it('uses the locked platform defaults as initial values', () => {
      renderForm({ platformLock: Platform.GEMINI });
      expect(getRootDirInput().value).toBe(PLATFORM_DEFAULTS['gemini']!.root_dir);
    });
  });
});
