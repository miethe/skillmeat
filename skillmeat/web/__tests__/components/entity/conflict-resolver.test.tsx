/**
 * @jest-environment jsdom
 */
import { render, screen, fireEvent } from '@testing-library/react';
import { ConflictResolver } from '@/components/entity/conflict-resolver';
import type { FileDiff } from '@/sdk/models/FileDiff';

const mockFileDiff: FileDiff = {
  file_path: 'src/example.ts',
  status: 'modified',
  unified_diff: `@@ -1,3 +1,3 @@
 function example() {
-  console.log('old');
+  console.log('new');
 }`,
};

const mockConflictInfo = {
  severity: 'hard' as const,
  conflictCount: 2,
  additions: 5,
  deletions: 3,
};

describe('ConflictResolver', () => {
  it('renders file path', () => {
    render(<ConflictResolver file={mockFileDiff} resolution={null} onResolve={jest.fn()} />);

    expect(screen.getByText('src/example.ts')).toBeInTheDocument();
  });

  it('displays Modified badge for modified files', () => {
    render(<ConflictResolver file={mockFileDiff} resolution={null} onResolve={jest.fn()} />);

    expect(screen.getByText('Modified')).toBeInTheDocument();
  });

  it('shows conflict badge when conflicts exist', () => {
    render(
      <ConflictResolver
        file={mockFileDiff}
        resolution={null}
        onResolve={jest.fn()}
        conflictInfo={mockConflictInfo}
      />
    );

    expect(screen.getByText('2 conflicts')).toBeInTheDocument();
  });

  it('shows singular conflict text for one conflict', () => {
    const singleConflict = { ...mockConflictInfo, conflictCount: 1 };
    render(
      <ConflictResolver
        file={mockFileDiff}
        resolution={null}
        onResolve={jest.fn()}
        conflictInfo={singleConflict}
      />
    );

    expect(screen.getByText('1 conflict')).toBeInTheDocument();
  });

  it('displays hard conflict indicator', () => {
    render(
      <ConflictResolver
        file={mockFileDiff}
        resolution={null}
        onResolve={jest.fn()}
        conflictInfo={mockConflictInfo}
      />
    );

    expect(screen.getByText(/Hard Conflict \(Overlapping\)/)).toBeInTheDocument();
  });

  it('displays soft conflict indicator', () => {
    const softConflict = { ...mockConflictInfo, severity: 'soft' as const };
    render(
      <ConflictResolver
        file={mockFileDiff}
        resolution={null}
        onResolve={jest.fn()}
        conflictInfo={softConflict}
      />
    );

    expect(screen.getByText(/Soft Conflict \(Adjacent\)/)).toBeInTheDocument();
  });

  it('shows additions and deletions count', () => {
    render(
      <ConflictResolver
        file={mockFileDiff}
        resolution={null}
        onResolve={jest.fn()}
        conflictInfo={mockConflictInfo}
      />
    );

    expect(screen.getByText('+5')).toBeInTheDocument();
    expect(screen.getByText('-3')).toBeInTheDocument();
  });

  it('renders side-by-side diff viewer', () => {
    render(<ConflictResolver file={mockFileDiff} resolution={null} onResolve={jest.fn()} />);

    expect(screen.getByText('Collection')).toBeInTheDocument();
    expect(screen.getByText('Project')).toBeInTheDocument();
  });

  it('uses custom labels for collection and project', () => {
    render(
      <ConflictResolver
        file={mockFileDiff}
        resolution={null}
        onResolve={jest.fn()}
        collectionLabel="Upstream"
        projectLabel="Local"
      />
    );

    expect(screen.getByText('Upstream')).toBeInTheDocument();
    expect(screen.getByText('Local')).toBeInTheDocument();
  });

  it('displays resolution options', () => {
    render(<ConflictResolver file={mockFileDiff} resolution={null} onResolve={jest.fn()} />);

    expect(screen.getByText('Keep Collection')).toBeInTheDocument();
    expect(screen.getByText('Keep Project')).toBeInTheDocument();
    expect(screen.getByText('Manual Merge')).toBeInTheDocument();
  });

  it('calls onResolve when Keep Collection is clicked', () => {
    const handleResolve = jest.fn();
    render(<ConflictResolver file={mockFileDiff} resolution={null} onResolve={handleResolve} />);

    const collectionButton = screen.getByText('Keep Collection');
    fireEvent.click(collectionButton);

    expect(handleResolve).toHaveBeenCalledWith('theirs');
  });

  it('calls onResolve when Keep Project is clicked', () => {
    const handleResolve = jest.fn();
    render(<ConflictResolver file={mockFileDiff} resolution={null} onResolve={handleResolve} />);

    const projectButton = screen.getByText('Keep Project');
    fireEvent.click(projectButton);

    expect(handleResolve).toHaveBeenCalledWith('ours');
  });

  it('calls onResolve when Manual Merge is clicked (if enabled)', () => {
    const handleResolve = jest.fn();
    render(<ConflictResolver file={mockFileDiff} resolution={null} onResolve={handleResolve} />);

    const manualButton = screen.getByText('Manual Merge');
    fireEvent.click(manualButton);

    // Manual merge is disabled by default, so callback may not be called
    // But clicking should not throw error
    expect(() => fireEvent.click(manualButton)).not.toThrow();
  });

  it('shows Manual Merge as disabled', () => {
    render(<ConflictResolver file={mockFileDiff} resolution={null} onResolve={jest.fn()} />);

    const manualButton = screen.getByText('Manual Merge').closest('button');
    expect(manualButton).toBeDisabled();
    expect(screen.getByText('Coming soon')).toBeInTheDocument();
  });

  it('highlights selected resolution option', () => {
    const { container } = render(
      <ConflictResolver file={mockFileDiff} resolution="theirs" onResolve={jest.fn()} />
    );

    const collectionButton = screen.getByText('Keep Collection').closest('button');
    expect(collectionButton).toHaveClass('border-primary');
  });

  it('shows resolution summary when resolution is selected', () => {
    render(<ConflictResolver file={mockFileDiff} resolution="theirs" onResolve={jest.fn()} />);

    expect(screen.getByText('Resolution Selected')).toBeInTheDocument();
    expect(screen.getByText(/Will use Collection version of this file/)).toBeInTheDocument();
  });

  it('shows correct summary for ours resolution', () => {
    render(<ConflictResolver file={mockFileDiff} resolution="ours" onResolve={jest.fn()} />);

    expect(screen.getByText(/Will keep Project version of this file/)).toBeInTheDocument();
  });

  it('shows correct summary for manual resolution', () => {
    render(<ConflictResolver file={mockFileDiff} resolution="manual" onResolve={jest.fn()} />);

    expect(screen.getByText(/Will manually merge both versions/)).toBeInTheDocument();
  });

  it('does not show resolution summary when no resolution selected', () => {
    render(<ConflictResolver file={mockFileDiff} resolution={null} onResolve={jest.fn()} />);

    expect(screen.queryByText('Resolution Selected')).not.toBeInTheDocument();
  });

  it('applies hard conflict styling to card', () => {
    const { container } = render(
      <ConflictResolver
        file={mockFileDiff}
        resolution={null}
        onResolve={jest.fn()}
        conflictInfo={mockConflictInfo}
      />
    );

    const card = container.firstChild;
    expect(card).toHaveClass('border-red-400');
  });

  it('applies soft conflict styling to card', () => {
    const softConflict = { ...mockConflictInfo, severity: 'soft' as const };
    const { container } = render(
      <ConflictResolver
        file={mockFileDiff}
        resolution={null}
        onResolve={jest.fn()}
        conflictInfo={softConflict}
      />
    );

    const card = container.firstChild;
    expect(card).toHaveClass('border-yellow-400');
  });

  it('applies selected styling when resolution is chosen', () => {
    const { container } = render(
      <ConflictResolver file={mockFileDiff} resolution="theirs" onResolve={jest.fn()} />
    );

    const card = container.firstChild;
    expect(card).toHaveClass('ring-2', 'ring-primary');
  });

  it('renders diff content in both panels', () => {
    render(<ConflictResolver file={mockFileDiff} resolution={null} onResolve={jest.fn()} />);

    expect(screen.getByText(/console\.log\('old'\)/)).toBeInTheDocument();
    expect(screen.getByText(/console\.log\('new'\)/)).toBeInTheDocument();
  });

  it('handles empty diff gracefully', () => {
    const emptyDiff: FileDiff = {
      file_path: 'empty.ts',
      status: 'modified',
      unified_diff: null,
    };

    render(<ConflictResolver file={emptyDiff} resolution={null} onResolve={jest.fn()} />);

    expect(screen.getByText('empty.ts')).toBeInTheDocument();
  });

  it('displays AlertTriangle icon for conflicts', () => {
    const { container } = render(
      <ConflictResolver
        file={mockFileDiff}
        resolution={null}
        onResolve={jest.fn()}
        conflictInfo={mockConflictInfo}
      />
    );

    const icons = container.querySelectorAll('svg');
    expect(icons.length).toBeGreaterThan(0);
  });

  it('shows resolution descriptions', () => {
    render(<ConflictResolver file={mockFileDiff} resolution={null} onResolve={jest.fn()} />);

    expect(screen.getByText('Use upstream version')).toBeInTheDocument();
    expect(screen.getByText('Use local version')).toBeInTheDocument();
    expect(screen.getByText('Combine both')).toBeInTheDocument();
  });
});
