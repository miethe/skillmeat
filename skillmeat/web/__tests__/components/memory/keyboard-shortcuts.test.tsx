/**
 * @jest-environment jsdom
 *
 * Tests for useKeyboardShortcuts hook (TEST-3.15)
 *
 * Validates keyboard navigation and triage shortcuts for the Memory Inbox.
 */
import { renderHook } from '@testing-library/react';
import { fireEvent } from '@testing-library/react';
import { useRef, type RefObject } from 'react';
import {
  useKeyboardShortcuts,
  type KeyboardShortcutActions,
} from '@/hooks/use-keyboard-shortcuts';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Create a mock actions object with jest.fn() for every callback.
 */
function createMockActions(
  overrides: Partial<KeyboardShortcutActions> = {}
): KeyboardShortcutActions {
  return {
    onNavigateDown: jest.fn(),
    onNavigateUp: jest.fn(),
    onApprove: jest.fn(),
    onEdit: jest.fn(),
    onReject: jest.fn(),
    onMerge: jest.fn(),
    onToggleSelect: jest.fn(),
    onOpenDetail: jest.fn(),
    onDismiss: jest.fn(),
    onSelectAll: jest.fn(),
    onShowHelp: jest.fn(),
    itemCount: 10,
    ...overrides,
  };
}

/**
 * Mount the hook attached to a real DOM container element.
 *
 * Returns the container, actions, and an `update` helper to re-render
 * with new props.
 */
function setupHook(
  actionsOverrides: Partial<KeyboardShortcutActions> = {},
  enabled = true
) {
  const container = document.createElement('div');
  document.body.appendChild(container);

  const actions = createMockActions(actionsOverrides);

  const { unmount, rerender } = renderHook(
    ({
      actions: a,
      enabled: e,
    }: {
      actions: KeyboardShortcutActions;
      enabled: boolean;
    }) => {
      const ref = useRef<HTMLElement>(container);
      useKeyboardShortcuts(ref, a, e);
      return ref;
    },
    {
      initialProps: { actions, enabled },
    }
  );

  return { container, actions, unmount, rerender };
}

/**
 * Convenience: fire a keydown event on a container element.
 */
function pressKey(
  container: HTMLElement,
  key: string,
  options: Partial<KeyboardEventInit> = {}
) {
  fireEvent.keyDown(container, { key, ...options });
}

// ---------------------------------------------------------------------------
// Cleanup
// ---------------------------------------------------------------------------

afterEach(() => {
  // Remove any containers added to the body
  document.body.innerHTML = '';
});

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('useKeyboardShortcuts', () => {
  describe('Navigation keys', () => {
    it('j key calls onNavigateDown', () => {
      const { container, actions } = setupHook();

      pressKey(container, 'j');

      expect(actions.onNavigateDown).toHaveBeenCalledTimes(1);
    });

    it('k key calls onNavigateUp', () => {
      const { container, actions } = setupHook();

      pressKey(container, 'k');

      expect(actions.onNavigateUp).toHaveBeenCalledTimes(1);
    });
  });

  describe('Action keys', () => {
    it('a key calls onApprove', () => {
      const { container, actions } = setupHook();

      pressKey(container, 'a');

      expect(actions.onApprove).toHaveBeenCalledTimes(1);
    });

    it('e key calls onEdit', () => {
      const { container, actions } = setupHook();

      pressKey(container, 'e');

      expect(actions.onEdit).toHaveBeenCalledTimes(1);
    });

    it('r key calls onReject', () => {
      const { container, actions } = setupHook();

      pressKey(container, 'r');

      expect(actions.onReject).toHaveBeenCalledTimes(1);
    });

    it('m key calls onMerge', () => {
      const { container, actions } = setupHook();

      pressKey(container, 'm');

      expect(actions.onMerge).toHaveBeenCalledTimes(1);
    });
  });

  describe('Selection and detail keys', () => {
    it('Space key calls onToggleSelect', () => {
      const { container, actions } = setupHook();

      pressKey(container, ' ');

      expect(actions.onToggleSelect).toHaveBeenCalledTimes(1);
    });

    it('Space key prevents default to avoid scrolling', () => {
      const { container } = setupHook();

      const event = new KeyboardEvent('keydown', {
        key: ' ',
        bubbles: true,
        cancelable: true,
      });
      const preventDefaultSpy = jest.spyOn(event, 'preventDefault');
      container.dispatchEvent(event);

      expect(preventDefaultSpy).toHaveBeenCalled();
    });

    it('Enter key calls onOpenDetail', () => {
      const { container, actions } = setupHook();

      pressKey(container, 'Enter');

      expect(actions.onOpenDetail).toHaveBeenCalledTimes(1);
    });

    it('Escape key calls onDismiss', () => {
      const { container, actions } = setupHook();

      pressKey(container, 'Escape');

      expect(actions.onDismiss).toHaveBeenCalledTimes(1);
    });
  });

  describe('Multi-select and help', () => {
    it('Cmd+A calls onSelectAll', () => {
      const { container, actions } = setupHook();

      pressKey(container, 'a', { metaKey: true });

      expect(actions.onSelectAll).toHaveBeenCalledTimes(1);
      // Should NOT also call onApprove
      expect(actions.onApprove).not.toHaveBeenCalled();
    });

    it('Ctrl+A calls onSelectAll', () => {
      const { container, actions } = setupHook();

      pressKey(container, 'a', { ctrlKey: true });

      expect(actions.onSelectAll).toHaveBeenCalledTimes(1);
      expect(actions.onApprove).not.toHaveBeenCalled();
    });

    it('Cmd+A prevents default browser select-all', () => {
      const { container } = setupHook();

      const event = new KeyboardEvent('keydown', {
        key: 'a',
        metaKey: true,
        bubbles: true,
        cancelable: true,
      });
      const preventDefaultSpy = jest.spyOn(event, 'preventDefault');
      container.dispatchEvent(event);

      expect(preventDefaultSpy).toHaveBeenCalled();
    });

    it('? key calls onShowHelp', () => {
      const { container, actions } = setupHook();

      pressKey(container, '?');

      expect(actions.onShowHelp).toHaveBeenCalledTimes(1);
    });
  });

  describe('Disabled state', () => {
    it('shortcuts do not fire when enabled is false', () => {
      const { container, actions } = setupHook({}, false);

      pressKey(container, 'j');
      pressKey(container, 'k');
      pressKey(container, 'a');
      pressKey(container, 'e');
      pressKey(container, ' ');
      pressKey(container, 'Enter');
      pressKey(container, 'Escape');
      pressKey(container, '?');

      expect(actions.onNavigateDown).not.toHaveBeenCalled();
      expect(actions.onNavigateUp).not.toHaveBeenCalled();
      expect(actions.onApprove).not.toHaveBeenCalled();
      expect(actions.onEdit).not.toHaveBeenCalled();
      expect(actions.onToggleSelect).not.toHaveBeenCalled();
      expect(actions.onOpenDetail).not.toHaveBeenCalled();
      expect(actions.onDismiss).not.toHaveBeenCalled();
      expect(actions.onShowHelp).not.toHaveBeenCalled();
    });
  });

  describe('Input element suppression', () => {
    it('shortcuts disabled when focus is in an input element', () => {
      const { container, actions } = setupHook();

      // Create an input element and focus it
      const input = document.createElement('input');
      document.body.appendChild(input);
      input.focus();

      pressKey(container, 'j');
      pressKey(container, 'a');

      expect(actions.onNavigateDown).not.toHaveBeenCalled();
      expect(actions.onApprove).not.toHaveBeenCalled();
    });

    it('shortcuts disabled when focus is in a textarea element', () => {
      const { container, actions } = setupHook();

      const textarea = document.createElement('textarea');
      document.body.appendChild(textarea);
      textarea.focus();

      pressKey(container, 'j');
      pressKey(container, 'e');

      expect(actions.onNavigateDown).not.toHaveBeenCalled();
      expect(actions.onEdit).not.toHaveBeenCalled();
    });

    it('shortcuts disabled when focus is in a select element', () => {
      const { container, actions } = setupHook();

      const select = document.createElement('select');
      document.body.appendChild(select);
      select.focus();

      pressKey(container, 'r');

      expect(actions.onReject).not.toHaveBeenCalled();
    });

    it('shortcuts disabled when focus is in a contenteditable element', () => {
      const { container, actions } = setupHook();

      const editable = document.createElement('div');
      editable.setAttribute('contenteditable', 'true');
      document.body.appendChild(editable);
      editable.focus();

      pressKey(container, 'k');

      expect(actions.onNavigateUp).not.toHaveBeenCalled();
    });
  });

  describe('Modifier key passthrough', () => {
    it('ignores keys with Alt modifier (except Ctrl/Cmd+A)', () => {
      const { container, actions } = setupHook();

      pressKey(container, 'j', { altKey: true });

      expect(actions.onNavigateDown).not.toHaveBeenCalled();
    });

    it('ignores keys with Ctrl modifier other than Ctrl+A', () => {
      const { container, actions } = setupHook();

      // Ctrl+E should not call onEdit (it is a browser shortcut)
      pressKey(container, 'e', { ctrlKey: true });

      expect(actions.onEdit).not.toHaveBeenCalled();
    });
  });

  describe('Unrecognized keys', () => {
    it('does not call any action for unrecognized keys', () => {
      const { container, actions } = setupHook();

      pressKey(container, 'z');
      pressKey(container, 'x');
      pressKey(container, 'Tab');

      expect(actions.onNavigateDown).not.toHaveBeenCalled();
      expect(actions.onNavigateUp).not.toHaveBeenCalled();
      expect(actions.onApprove).not.toHaveBeenCalled();
      expect(actions.onEdit).not.toHaveBeenCalled();
      expect(actions.onReject).not.toHaveBeenCalled();
      expect(actions.onMerge).not.toHaveBeenCalled();
      expect(actions.onToggleSelect).not.toHaveBeenCalled();
      expect(actions.onOpenDetail).not.toHaveBeenCalled();
      expect(actions.onDismiss).not.toHaveBeenCalled();
      expect(actions.onSelectAll).not.toHaveBeenCalled();
      expect(actions.onShowHelp).not.toHaveBeenCalled();
    });
  });

  describe('Cleanup', () => {
    it('removes event listener on unmount', () => {
      const { container, actions, unmount } = setupHook();

      unmount();

      // After unmount, events should not fire
      pressKey(container, 'j');
      expect(actions.onNavigateDown).not.toHaveBeenCalled();
    });
  });
});
