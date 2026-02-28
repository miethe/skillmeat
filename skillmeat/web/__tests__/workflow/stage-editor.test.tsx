/**
 * @jest-environment jsdom
 *
 * Tests for StageEditor component.
 *
 * Focus areas:
 *   - Renders all 4 sections (Basic Info, Roles, Context, Advanced)
 *   - Advanced section is collapsed by default (aria-expanded=false) and toggleable
 *   - Save button is disabled when no changes have been made
 *   - Save button calls onSave with updated stage data on click
 *   - Cancel / close button calls onClose
 *
 * Implementation note on section collapse:
 *   The Section component renders a content div with `hidden={!open}`. The
 *   HTML `hidden` attribute hides the element visually but JSDOM still allows
 *   queries to traverse it (getByLabelText finds hidden inputs). We therefore
 *   test collapse/expand state via the button's `aria-expanded` attribute,
 *   which is the accessible and reliable signal.
 */

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { StageEditor } from '@/components/workflow/stage-editor';
import type { WorkflowStage } from '@/types/workflow';

// ---------------------------------------------------------------------------
// Shallow-mock heavy shared components to keep the test fast and focused.
// ---------------------------------------------------------------------------

jest.mock('@/components/shared/slide-over-panel', () => ({
  SlideOverPanel: ({
    children,
    open,
    title,
    onClose,
  }: {
    children: React.ReactNode;
    open: boolean;
    title: string;
    onClose: () => void;
  }) =>
    open ? (
      <div role="dialog" aria-label={title}>
        {children}
        <button onClick={onClose}>ClosePanel</button>
      </div>
    ) : null,
}));

jest.mock('@/components/shared/artifact-picker', () => ({
  ArtifactPicker: ({ label }: { label: string }) => (
    <div data-testid={`artifact-picker-${label.toLowerCase().replace(/\s+/g, '-')}`}>
      {label}
    </div>
  ),
}));

jest.mock('@/components/shared/context-module-picker', () => ({
  ContextModulePicker: ({ label }: { label: string }) => (
    <div data-testid="context-module-picker">{label}</div>
  ),
}));

// ---------------------------------------------------------------------------
// Fixture
// ---------------------------------------------------------------------------

function makeStage(overrides: Partial<WorkflowStage> = {}): WorkflowStage {
  return {
    id: 'stage-001',
    stageIdRef: 'build',
    name: 'Build',
    description: 'Compiles and packages the application',
    orderIndex: 0,
    stageType: 'agent',
    dependsOn: [],
    inputs: {},
    outputs: {},
    roles: {
      primary: { artifact: 'agent:builder' },
      tools: [],
    },
    context: { modules: [] },
    errorPolicy: {
      onFailure: 'halt',
      timeout: '60s',
      retry: { maxAttempts: 2, initialInterval: '30s', backoffMultiplier: 2, maxInterval: '5m', nonRetryableErrors: [] },
    },
    ...overrides,
  };
}

function renderEditor(props: Partial<Parameters<typeof StageEditor>[0]> = {}) {
  const defaults = {
    stage: makeStage(),
    open: true,
    onClose: jest.fn(),
    onSave: jest.fn(),
  };
  return render(<StageEditor {...defaults} {...props} />);
}

// Helper: find the section toggle button by its text label
function getSectionButton(name: RegExp | string) {
  return screen.getByRole('button', { name });
}

// ---------------------------------------------------------------------------
// Section visibility
// ---------------------------------------------------------------------------

describe('StageEditor — sections', () => {
  it('renders the Basic Info section heading', () => {
    renderEditor();
    expect(screen.getByText('Basic Info')).toBeInTheDocument();
  });

  it('renders the Roles section heading', () => {
    renderEditor();
    expect(screen.getByText('Roles')).toBeInTheDocument();
  });

  it('renders the Context Policy section heading', () => {
    renderEditor();
    expect(screen.getByText('Context Policy')).toBeInTheDocument();
  });

  it('renders the Advanced section heading', () => {
    renderEditor();
    expect(screen.getByText('Advanced')).toBeInTheDocument();
  });

  it('has Basic Info content visible by default (Name field)', () => {
    renderEditor();
    expect(screen.getByLabelText('Name')).toBeInTheDocument();
  });

  it('has Roles content visible by default', () => {
    renderEditor();
    expect(screen.getByTestId('artifact-picker-primary-agent')).toBeInTheDocument();
  });

  it('has Context Policy content visible by default', () => {
    renderEditor();
    expect(screen.getByTestId('context-module-picker')).toBeInTheDocument();
  });

  it('Advanced section toggle has aria-expanded="false" by default (collapsed)', () => {
    renderEditor();
    const advancedButton = getSectionButton(/Advanced/i);
    expect(advancedButton).toHaveAttribute('aria-expanded', 'false');
  });

  it('Advanced section toggle has aria-expanded="true" after clicking to expand', async () => {
    const user = userEvent.setup();
    renderEditor();
    const advancedButton = getSectionButton(/Advanced/i);
    await user.click(advancedButton);
    expect(advancedButton).toHaveAttribute('aria-expanded', 'true');
  });

  it('Advanced section collapses again when clicked a second time', async () => {
    const user = userEvent.setup();
    renderEditor();
    const advancedButton = getSectionButton(/Advanced/i);
    await user.click(advancedButton); // open → aria-expanded=true
    await user.click(advancedButton); // close → aria-expanded=false
    expect(advancedButton).toHaveAttribute('aria-expanded', 'false');
  });

  it('Advanced section content is accessible after expanding', async () => {
    const user = userEvent.setup();
    renderEditor();
    // Click the toggle (section's aria-controls content div removes hidden)
    const advancedButton = getSectionButton(/Advanced/i);
    await user.click(advancedButton);
    // The timeout input should not be inside a hidden container anymore
    const contentId = advancedButton.getAttribute('aria-controls');
    const contentDiv = document.getElementById(contentId!);
    expect(contentDiv).not.toBeNull();
    expect(contentDiv).not.toHaveAttribute('hidden');
  });
});

// ---------------------------------------------------------------------------
// Save / Cancel behaviour
// ---------------------------------------------------------------------------

describe('StageEditor — Save button', () => {
  it('Save button is disabled when no changes have been made', () => {
    renderEditor();
    expect(screen.getByRole('button', { name: /Save/i })).toBeDisabled();
  });

  it('Save button becomes enabled after changing the name', async () => {
    const user = userEvent.setup();
    renderEditor();
    await user.clear(screen.getByLabelText('Name'));
    await user.type(screen.getByLabelText('Name'), 'Updated Name');
    expect(screen.getByRole('button', { name: /Save/i })).not.toBeDisabled();
  });

  it('Save button stays disabled when name is cleared to empty', async () => {
    const user = userEvent.setup();
    renderEditor();
    await user.clear(screen.getByLabelText('Name'));
    expect(screen.getByRole('button', { name: /Save/i })).toBeDisabled();
  });

  it('calls onSave when Save button is clicked after a change', async () => {
    const user = userEvent.setup();
    const onSave = jest.fn();
    renderEditor({ onSave });
    await user.clear(screen.getByLabelText('Name'));
    await user.type(screen.getByLabelText('Name'), 'Renamed Stage');
    await user.click(screen.getByRole('button', { name: /Save/i }));
    expect(onSave).toHaveBeenCalledTimes(1);
  });

  it('onSave receives an updated WorkflowStage with the new name', async () => {
    const user = userEvent.setup();
    const onSave = jest.fn();
    renderEditor({ onSave });
    await user.clear(screen.getByLabelText('Name'));
    await user.type(screen.getByLabelText('Name'), 'Pipeline Build');
    await user.click(screen.getByRole('button', { name: /Save/i }));
    const savedStage = onSave.mock.calls[0][0] as WorkflowStage;
    expect(savedStage.name).toBe('Pipeline Build');
  });
});

describe('StageEditor — Cancel / close', () => {
  it('calls onClose when Cancel button is clicked', async () => {
    const user = userEvent.setup();
    const onClose = jest.fn();
    renderEditor({ onClose });
    await user.click(screen.getByRole('button', { name: /Cancel/i }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});

// ---------------------------------------------------------------------------
// Null stage
// ---------------------------------------------------------------------------

describe('StageEditor — null stage', () => {
  it('renders without errors when stage is null', () => {
    expect(() => renderEditor({ stage: null })).not.toThrow();
  });

  it('Save button is disabled when stage is null (nothing to save)', () => {
    renderEditor({ stage: null });
    expect(screen.getByRole('button', { name: /Save/i })).toBeDisabled();
  });
});

// ---------------------------------------------------------------------------
// Panel not rendered when closed
// ---------------------------------------------------------------------------

describe('StageEditor — closed state', () => {
  it('does not render the dialog when open is false', () => {
    renderEditor({ open: false });
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });
});
