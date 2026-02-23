/**
 * @jest-environment jsdom
 *
 * Tests for ArtifactPartOfSection component
 *
 * Covers:
 * - Member artifact shows "Part of" section with parent skill name
 * - Member artifact shows "Part of" section with parent plugin name (regression)
 * - Multiple parents are all listed
 * - Loading state: shows skeleton with ARIA label
 * - Empty/null state: component returns null when no parents
 * - Navigation links: correct href and descriptive aria-labels
 * - Accessibility: semantic list, heading, link labels
 */

import React from 'react';
import { render, screen, within } from '@testing-library/react';
import { ArtifactPartOfSection } from '@/components/artifact/artifact-part-of-section';
import type { AssociationItemDTO } from '@/types/associations';

// ---------------------------------------------------------------------------
// Factory helpers
// ---------------------------------------------------------------------------

function createMockParent(overrides?: Partial<AssociationItemDTO>): AssociationItemDTO {
  return {
    artifact_id: 'composite:my-plugin',
    artifact_name: 'my-plugin',
    artifact_type: 'composite',
    relationship_type: 'contains',
    pinned_version_hash: null,
    created_at: '2026-01-15T10:00:00Z',
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('ArtifactPartOfSection', () => {
  // -------------------------------------------------------------------------
  // Scenario 2: Member shows "Part of" section with skill parent
  // -------------------------------------------------------------------------

  describe('showing a skill parent', () => {
    const skillParent = createMockParent({
      artifact_id: 'skill:dev-workflow',
      artifact_name: 'dev-workflow',
      artifact_type: 'skill',
    });

    it('renders "Part of" heading when skill parent exists', () => {
      render(
        <ArtifactPartOfSection parents={[skillParent]} isLoading={false} />
      );

      expect(screen.getByText('Part of')).toBeInTheDocument();
    });

    it('shows the skill parent name in the section', () => {
      render(
        <ArtifactPartOfSection parents={[skillParent]} isLoading={false} />
      );

      expect(screen.getByText('dev-workflow')).toBeInTheDocument();
    });

    it('renders a navigable link to the skill parent detail page', () => {
      render(
        <ArtifactPartOfSection parents={[skillParent]} isLoading={false} />
      );

      const link = screen.getByRole('link', {
        name: /open dev-workflow skill detail page/i,
      });
      expect(link).toBeInTheDocument();
      expect(link).toHaveAttribute(
        'href',
        '/artifacts/skill%3Adev-workflow'
      );
    });

    it('shows the parent type label next to the parent name', () => {
      render(
        <ArtifactPartOfSection parents={[skillParent]} isLoading={false} />
      );

      // The type label is capitalised by the component
      expect(screen.getByText('Skill')).toBeInTheDocument();
    });

    it('renders the section with correct ARIA label', () => {
      render(
        <ArtifactPartOfSection parents={[skillParent]} isLoading={false} />
      );

      const section = screen.getByRole('region', {
        name: /parent composites that contain this artifact/i,
      });
      expect(section).toBeInTheDocument();
    });
  });

  // -------------------------------------------------------------------------
  // Scenario 3 (regression): Member shows plugin parent correctly
  // -------------------------------------------------------------------------

  describe('showing a plugin parent (regression)', () => {
    const pluginParent = createMockParent({
      artifact_id: 'composite:design-suite',
      artifact_name: 'design-suite',
      artifact_type: 'composite',
    });

    it('renders "Part of" heading when plugin/composite parent exists', () => {
      render(
        <ArtifactPartOfSection parents={[pluginParent]} isLoading={false} />
      );

      expect(screen.getByText('Part of')).toBeInTheDocument();
    });

    it('shows the plugin parent name in the section', () => {
      render(
        <ArtifactPartOfSection parents={[pluginParent]} isLoading={false} />
      );

      expect(screen.getByText('design-suite')).toBeInTheDocument();
    });

    it('renders a navigable link to the composite parent', () => {
      render(
        <ArtifactPartOfSection parents={[pluginParent]} isLoading={false} />
      );

      const link = screen.getByRole('link', {
        name: /open design-suite composite detail page/i,
      });
      expect(link).toBeInTheDocument();
      expect(link).toHaveAttribute(
        'href',
        '/artifacts/composite%3Adesign-suite'
      );
    });

    it('shows "Composite" type label for composite artifact_type', () => {
      render(
        <ArtifactPartOfSection parents={[pluginParent]} isLoading={false} />
      );

      expect(screen.getByText('Composite')).toBeInTheDocument();
    });
  });

  // -------------------------------------------------------------------------
  // Multiple parents
  // -------------------------------------------------------------------------

  describe('multiple parents', () => {
    const parents: AssociationItemDTO[] = [
      createMockParent({
        artifact_id: 'skill:dev-workflow',
        artifact_name: 'dev-workflow',
        artifact_type: 'skill',
      }),
      createMockParent({
        artifact_id: 'composite:mega-bundle',
        artifact_name: 'mega-bundle',
        artifact_type: 'composite',
      }),
    ];

    it('renders all parent names when multiple parents exist', () => {
      render(<ArtifactPartOfSection parents={parents} isLoading={false} />);

      expect(screen.getByText('dev-workflow')).toBeInTheDocument();
      expect(screen.getByText('mega-bundle')).toBeInTheDocument();
    });

    it('renders a list with role="list" for multiple parents', () => {
      render(<ArtifactPartOfSection parents={parents} isLoading={false} />);

      const list = screen.getByRole('list', { name: /parent composite list/i });
      expect(list).toBeInTheDocument();

      const items = within(list).getAllByRole('listitem');
      expect(items).toHaveLength(2);
    });

    it('each parent has a navigable link', () => {
      render(<ArtifactPartOfSection parents={parents} isLoading={false} />);

      const links = screen.getAllByRole('link');
      expect(links).toHaveLength(2);
    });
  });

  // -------------------------------------------------------------------------
  // Empty state — component returns null
  // -------------------------------------------------------------------------

  describe('empty state (no parents)', () => {
    it('renders nothing when parents array is empty and not loading', () => {
      const { container } = render(
        <ArtifactPartOfSection parents={[]} isLoading={false} />
      );

      // Component returns null — nothing in the DOM
      expect(container).toBeEmptyDOMElement();
    });

    it('does not render "Part of" heading when no parents', () => {
      render(<ArtifactPartOfSection parents={[]} isLoading={false} />);

      expect(screen.queryByText('Part of')).not.toBeInTheDocument();
    });
  });

  // -------------------------------------------------------------------------
  // Loading state
  // -------------------------------------------------------------------------

  describe('Loading state', () => {
    it('shows loading skeleton with correct ARIA label', () => {
      render(<ArtifactPartOfSection parents={[]} isLoading={true} />);

      const skeleton = screen.getByRole('status', {
        name: /loading parent composites/i,
      });
      expect(skeleton).toBeInTheDocument();
    });

    it('shows "Part of" heading even during loading', () => {
      render(<ArtifactPartOfSection parents={[]} isLoading={true} />);

      // The section with heading renders even while skeleton is shown
      expect(screen.getByText('Part of')).toBeInTheDocument();
    });

    it('does not render parent list items during loading', () => {
      const parentWithData = createMockParent({
        artifact_name: 'dev-workflow',
        artifact_type: 'skill',
      });

      render(
        <ArtifactPartOfSection parents={[parentWithData]} isLoading={true} />
      );

      // Skeleton replaces the list — no list items visible
      expect(screen.queryByRole('list', { name: /parent composite list/i })).not.toBeInTheDocument();
    });
  });

  // -------------------------------------------------------------------------
  // Accessibility
  // -------------------------------------------------------------------------

  describe('Accessibility', () => {
    const parent = createMockParent({
      artifact_id: 'skill:dev-workflow',
      artifact_name: 'dev-workflow',
      artifact_type: 'skill',
    });

    it('renders "Part of" as a visible heading element', () => {
      render(<ArtifactPartOfSection parents={[parent]} isLoading={false} />);

      const heading = screen.getByRole('heading', { name: /part of/i });
      expect(heading).toBeInTheDocument();
    });

    it('link has descriptive aria-label including artifact name and type', () => {
      render(<ArtifactPartOfSection parents={[parent]} isLoading={false} />);

      // aria-label pattern: "Open {name} {type} detail page"
      const link = screen.getByRole('link', {
        name: /open dev-workflow skill detail page/i,
      });
      expect(link).toBeInTheDocument();
    });

    it('section has aria-label "Parent composites that contain this artifact"', () => {
      render(<ArtifactPartOfSection parents={[parent]} isLoading={false} />);

      expect(
        screen.getByRole('region', {
          name: 'Parent composites that contain this artifact',
        })
      ).toBeInTheDocument();
    });
  });
});
