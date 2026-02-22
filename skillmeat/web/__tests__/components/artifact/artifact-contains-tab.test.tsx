/**
 * @jest-environment jsdom
 *
 * Tests for ArtifactContainsTab component
 *
 * Covers:
 * - Skill composite: shows "Skill Members" label with correct member count/names
 * - Plugin composite (regression): still shows "Plugin Members" label correctly
 * - Loading state: shows skeleton with correct ARIA label
 * - Error state: shows error UI with retry button
 * - Empty state: shows contextual empty message per compositeType
 * - Member rows: navigation links, aria-labels, type display
 */

import React from 'react';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ArtifactContainsTab } from '@/components/artifact/artifact-contains-tab';
import type { AssociationItemDTO } from '@/types/associations';

// ---------------------------------------------------------------------------
// Factory helpers
// ---------------------------------------------------------------------------

function createMockChild(overrides?: Partial<AssociationItemDTO>): AssociationItemDTO {
  return {
    artifact_id: 'command:my-command',
    artifact_name: 'my-command',
    artifact_type: 'command',
    relationship_type: 'contains',
    pinned_version_hash: null,
    created_at: '2026-01-15T10:00:00Z',
    ...overrides,
  };
}

const skillChildren: AssociationItemDTO[] = [
  createMockChild({
    artifact_id: 'command:format-code',
    artifact_name: 'format-code',
    artifact_type: 'command',
  }),
  createMockChild({
    artifact_id: 'agent:code-reviewer',
    artifact_name: 'code-reviewer',
    artifact_type: 'agent',
  }),
  createMockChild({
    artifact_id: 'hook:pre-commit',
    artifact_name: 'pre-commit',
    artifact_type: 'hook',
  }),
];

const pluginChildren: AssociationItemDTO[] = [
  createMockChild({
    artifact_id: 'skill:canvas-design',
    artifact_name: 'canvas-design',
    artifact_type: 'skill',
  }),
  createMockChild({
    artifact_id: 'command:deploy',
    artifact_name: 'deploy',
    artifact_type: 'command',
  }),
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const noop = () => {};

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('ArtifactContainsTab', () => {
  // -------------------------------------------------------------------------
  // Scenario 1: Skill artifact — shows "Skill Members" label
  // -------------------------------------------------------------------------

  describe('Skill composite type', () => {
    it('renders "Skill Members" section heading for compositeType="skill"', () => {
      render(
        <ArtifactContainsTab
          children={skillChildren}
          isLoading={false}
          error={null}
          onRetry={noop}
          compositeType="skill"
        />
      );

      // The label text "Skill Members" should appear
      expect(screen.getByText('Skill Members')).toBeInTheDocument();
    });

    it('shows correct member count for skill composite', () => {
      render(
        <ArtifactContainsTab
          children={skillChildren}
          isLoading={false}
          error={null}
          onRetry={noop}
          compositeType="skill"
        />
      );

      // "3 artifacts" count indicator
      expect(screen.getByText(/3 artifacts/)).toBeInTheDocument();
    });

    it('renders all member names for skill composite', () => {
      render(
        <ArtifactContainsTab
          children={skillChildren}
          isLoading={false}
          error={null}
          onRetry={noop}
          compositeType="skill"
        />
      );

      expect(screen.getByText('format-code')).toBeInTheDocument();
      expect(screen.getByText('code-reviewer')).toBeInTheDocument();
      expect(screen.getByText('pre-commit')).toBeInTheDocument();
    });

    it('renders member list with proper ARIA list role', () => {
      render(
        <ArtifactContainsTab
          children={skillChildren}
          isLoading={false}
          error={null}
          onRetry={noop}
          compositeType="skill"
        />
      );

      const list = screen.getByRole('list', { name: /child artifact list/i });
      expect(list).toBeInTheDocument();
      const items = within(list).getAllByRole('listitem');
      expect(items).toHaveLength(3);
    });

    it('renders navigable links for each skill member', () => {
      render(
        <ArtifactContainsTab
          children={skillChildren}
          isLoading={false}
          error={null}
          onRetry={noop}
          compositeType="skill"
        />
      );

      // Each member should have a link with descriptive aria-label
      expect(
        screen.getByRole('link', { name: /view format-code \(command\)/i })
      ).toBeInTheDocument();
      expect(
        screen.getByRole('link', { name: /view code-reviewer \(agent\)/i })
      ).toBeInTheDocument();
      expect(
        screen.getByRole('link', { name: /view pre-commit \(hook\)/i })
      ).toBeInTheDocument();
    });

    it('links point to correct artifact detail URLs', () => {
      render(
        <ArtifactContainsTab
          children={skillChildren}
          isLoading={false}
          error={null}
          onRetry={noop}
          compositeType="skill"
        />
      );

      const formatCodeLink = screen.getByRole('link', {
        name: /view format-code/i,
      });
      expect(formatCodeLink).toHaveAttribute(
        'href',
        '/artifacts/command%3Aformat-code'
      );

      const agentLink = screen.getByRole('link', {
        name: /view code-reviewer/i,
      });
      expect(agentLink).toHaveAttribute(
        'href',
        '/artifacts/agent%3Acode-reviewer'
      );
    });

    it('shows singular "artifact" for single member', () => {
      render(
        <ArtifactContainsTab
          children={[skillChildren[0]]}
          isLoading={false}
          error={null}
          onRetry={noop}
          compositeType="skill"
        />
      );

      expect(screen.getByText(/1 artifact\b/)).toBeInTheDocument();
    });

    it('renders section with correct aria-label for skill type', () => {
      render(
        <ArtifactContainsTab
          children={skillChildren}
          isLoading={false}
          error={null}
          onRetry={noop}
          compositeType="skill"
        />
      );

      const section = screen.getByRole('region', {
        name: /child artifacts contained in this skill/i,
      });
      expect(section).toBeInTheDocument();
    });
  });

  // -------------------------------------------------------------------------
  // Scenario 3 (regression): Plugin composite — shows "Plugin Members"
  // -------------------------------------------------------------------------

  describe('Plugin composite type (regression)', () => {
    it('renders "Plugin Members" section heading for compositeType="plugin"', () => {
      render(
        <ArtifactContainsTab
          children={pluginChildren}
          isLoading={false}
          error={null}
          onRetry={noop}
          compositeType="plugin"
        />
      );

      expect(screen.getByText('Plugin Members')).toBeInTheDocument();
    });

    it('shows correct member count for plugin composite', () => {
      render(
        <ArtifactContainsTab
          children={pluginChildren}
          isLoading={false}
          error={null}
          onRetry={noop}
          compositeType="plugin"
        />
      );

      expect(screen.getByText(/2 artifacts/)).toBeInTheDocument();
    });

    it('renders all member names for plugin composite', () => {
      render(
        <ArtifactContainsTab
          children={pluginChildren}
          isLoading={false}
          error={null}
          onRetry={noop}
          compositeType="plugin"
        />
      );

      expect(screen.getByText('canvas-design')).toBeInTheDocument();
      expect(screen.getByText('deploy')).toBeInTheDocument();
    });

    it('does NOT show "Skill Members" label for plugin composite', () => {
      render(
        <ArtifactContainsTab
          children={pluginChildren}
          isLoading={false}
          error={null}
          onRetry={noop}
          compositeType="plugin"
        />
      );

      expect(screen.queryByText('Skill Members')).not.toBeInTheDocument();
    });

    it('renders section with correct aria-label for plugin type', () => {
      render(
        <ArtifactContainsTab
          children={pluginChildren}
          isLoading={false}
          error={null}
          onRetry={noop}
          compositeType="plugin"
        />
      );

      const section = screen.getByRole('region', {
        name: /child artifacts contained in this plugin/i,
      });
      expect(section).toBeInTheDocument();
    });
  });

  // -------------------------------------------------------------------------
  // Additional composite type labels
  // -------------------------------------------------------------------------

  describe('Other composite types', () => {
    it('renders "Stack Members" for compositeType="stack"', () => {
      render(
        <ArtifactContainsTab
          children={[skillChildren[0]]}
          isLoading={false}
          error={null}
          onRetry={noop}
          compositeType="stack"
        />
      );

      expect(screen.getByText('Stack Members')).toBeInTheDocument();
    });

    it('renders "Suite Members" for compositeType="suite"', () => {
      render(
        <ArtifactContainsTab
          children={[skillChildren[0]]}
          isLoading={false}
          error={null}
          onRetry={noop}
          compositeType="suite"
        />
      );

      expect(screen.getByText('Suite Members')).toBeInTheDocument();
    });

    it('renders "Composite Members" as fallback when compositeType is undefined', () => {
      render(
        <ArtifactContainsTab
          children={[skillChildren[0]]}
          isLoading={false}
          error={null}
          onRetry={noop}
        />
      );

      expect(screen.getByText('Composite Members')).toBeInTheDocument();
    });
  });

  // -------------------------------------------------------------------------
  // Loading state
  // -------------------------------------------------------------------------

  describe('Loading state', () => {
    it('shows loading skeleton with correct ARIA label', () => {
      render(
        <ArtifactContainsTab
          children={[]}
          isLoading={true}
          error={null}
          onRetry={noop}
          compositeType="skill"
        />
      );

      const skeleton = screen.getByRole('status', {
        name: /loading child artifacts/i,
      });
      expect(skeleton).toBeInTheDocument();
    });

    it('does not render member list while loading', () => {
      render(
        <ArtifactContainsTab
          children={skillChildren}
          isLoading={true}
          error={null}
          onRetry={noop}
          compositeType="skill"
        />
      );

      expect(screen.queryByRole('list', { name: /child artifact list/i })).not.toBeInTheDocument();
      expect(screen.queryByText('format-code')).not.toBeInTheDocument();
    });
  });

  // -------------------------------------------------------------------------
  // Error state
  // -------------------------------------------------------------------------

  describe('Error state', () => {
    it('shows error UI with alert role', () => {
      render(
        <ArtifactContainsTab
          children={[]}
          isLoading={false}
          error={new Error('Network error')}
          onRetry={noop}
          compositeType="skill"
        />
      );

      expect(screen.getByRole('alert')).toBeInTheDocument();
    });

    it('shows "Failed to load child artifacts" message in error state', () => {
      render(
        <ArtifactContainsTab
          children={[]}
          isLoading={false}
          error={new Error('Network error')}
          onRetry={noop}
          compositeType="skill"
        />
      );

      expect(screen.getByText('Failed to load child artifacts')).toBeInTheDocument();
    });

    it('shows retry button in error state', () => {
      render(
        <ArtifactContainsTab
          children={[]}
          isLoading={false}
          error={new Error('Timeout')}
          onRetry={noop}
          compositeType="skill"
        />
      );

      expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument();
    });

    it('calls onRetry when retry button is clicked', async () => {
      const user = userEvent.setup();
      const onRetry = jest.fn();

      render(
        <ArtifactContainsTab
          children={[]}
          isLoading={false}
          error={new Error('Timeout')}
          onRetry={onRetry}
          compositeType="skill"
        />
      );

      await user.click(screen.getByRole('button', { name: /try again/i }));
      expect(onRetry).toHaveBeenCalledTimes(1);
    });
  });

  // -------------------------------------------------------------------------
  // Empty state
  // -------------------------------------------------------------------------

  describe('Empty state', () => {
    it('shows contextual empty message for skill type', () => {
      render(
        <ArtifactContainsTab
          children={[]}
          isLoading={false}
          error={null}
          onRetry={noop}
          compositeType="skill"
        />
      );

      expect(
        screen.getByText(/this skill contains no artifacts/i)
      ).toBeInTheDocument();
    });

    it('shows contextual empty message for plugin type', () => {
      render(
        <ArtifactContainsTab
          children={[]}
          isLoading={false}
          error={null}
          onRetry={noop}
          compositeType="plugin"
        />
      );

      expect(
        screen.getByText(/this plugin contains no artifacts/i)
      ).toBeInTheDocument();
    });

    it('does not render member list when children is empty', () => {
      render(
        <ArtifactContainsTab
          children={[]}
          isLoading={false}
          error={null}
          onRetry={noop}
          compositeType="skill"
        />
      );

      expect(screen.queryByRole('list', { name: /child artifact list/i })).not.toBeInTheDocument();
    });
  });

  // -------------------------------------------------------------------------
  // Member row display
  // -------------------------------------------------------------------------

  describe('Member row display', () => {
    it('shows capitalised type label beneath each member name', () => {
      render(
        <ArtifactContainsTab
          children={skillChildren}
          isLoading={false}
          error={null}
          onRetry={noop}
          compositeType="skill"
        />
      );

      // Types are capitalised by the component
      expect(screen.getByText('Command')).toBeInTheDocument();
      expect(screen.getByText('Agent')).toBeInTheDocument();
      expect(screen.getByText('Hook')).toBeInTheDocument();
    });
  });
});
