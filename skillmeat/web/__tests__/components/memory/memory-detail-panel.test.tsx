/**
 * @jest-environment jsdom
 */
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {
  MemoryDetailPanel,
  type MemoryDetailPanelProps,
} from '@/components/memory/memory-detail-panel';
import type { MemoryItemResponse } from '@/sdk/models/MemoryItemResponse';

// ---------------------------------------------------------------------------
// Mock data factory
// ---------------------------------------------------------------------------

function createMockMemory(overrides: Partial<MemoryItemResponse> = {}): MemoryItemResponse {
  return {
    id: 'test-id-1',
    project_id: 'project-1',
    type: 'constraint',
    content: 'Do not use default exports in components',
    confidence: 0.87,
    status: 'candidate',
    provenance: {
      source_type: 'session-extraction',
      session_id: 'sess-abc123',
      extracted_at: '2025-01-15T10:30:00Z',
      files: ['src/components/Button.tsx', 'src/components/Card.tsx'],
      commit_sha: 'abc1234def5678',
    },
    anchors: ['skillmeat/web/components'],
    ttl_policy: null,
    content_hash: 'hash123',
    access_count: 7,
    created_at: '2025-01-15T10:00:00Z',
    updated_at: '2025-01-16T14:00:00Z',
    deprecated_at: null,
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// Default props factory
// ---------------------------------------------------------------------------

function createDefaultProps(
  overrides: Partial<MemoryDetailPanelProps> = {}
): MemoryDetailPanelProps {
  return {
    memory: createMockMemory(),
    isOpen: true,
    onClose: jest.fn(),
    onEdit: jest.fn(),
    onApprove: jest.fn(),
    onReject: jest.fn(),
    onMerge: jest.fn(),
    onDeprecate: jest.fn(),
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('MemoryDetailPanel', () => {
  describe('Visibility', () => {
    it('applies translate-x-0 when isOpen is true', () => {
      const props = createDefaultProps({ isOpen: true });
      render(<MemoryDetailPanel {...props} />);

      const panel = screen.getByRole('complementary');
      expect(panel).toHaveClass('translate-x-0');
    });

    it('applies translate-x-full when isOpen is false', () => {
      const props = createDefaultProps({ isOpen: false });
      render(<MemoryDetailPanel {...props} />);

      const panel = screen.getByRole('complementary');
      expect(panel).toHaveClass('translate-x-full');
    });
  });

  describe('Content rendering', () => {
    it('renders memory content when isOpen and memory provided', () => {
      const props = createDefaultProps();
      render(<MemoryDetailPanel {...props} />);

      expect(
        screen.getByText('Do not use default exports in components')
      ).toBeInTheDocument();
    });

    it('shows type badge', () => {
      const props = createDefaultProps();
      render(<MemoryDetailPanel {...props} />);

      expect(screen.getByText('Constraint')).toBeInTheDocument();
    });

    it('shows status badge', () => {
      const props = createDefaultProps();
      render(<MemoryDetailPanel {...props} />);

      expect(screen.getByText('candidate')).toBeInTheDocument();
    });

    it('shows confidence display with progress bar', () => {
      const props = createDefaultProps();
      render(<MemoryDetailPanel {...props} />);

      expect(screen.getByText('87%')).toBeInTheDocument();
      expect(screen.getByRole('progressbar')).toBeInTheDocument();
      expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '87');
    });

    it('shows access stats', () => {
      const props = createDefaultProps();
      render(<MemoryDetailPanel {...props} />);

      expect(screen.getByText('7')).toBeInTheDocument();
      expect(screen.getByText(/times/)).toBeInTheDocument();
    });

    it('uses singular "time" for access_count of 1', () => {
      const memory = createMockMemory({ access_count: 1 });
      const props = createDefaultProps({ memory });
      render(<MemoryDetailPanel {...props} />);

      expect(screen.getByText(/time(?!s)/)).toBeInTheDocument();
    });

    it('shows empty state when memory is null', () => {
      const props = createDefaultProps({ memory: null });
      render(<MemoryDetailPanel {...props} />);

      expect(
        screen.getByText('Select a memory to view details')
      ).toBeInTheDocument();
    });

    it('shows "Memory Detail" heading', () => {
      const props = createDefaultProps();
      render(<MemoryDetailPanel {...props} />);

      expect(screen.getByText('Memory Detail')).toBeInTheDocument();
    });
  });

  describe('Provenance section', () => {
    it('shows provenance section', () => {
      const props = createDefaultProps();
      render(<MemoryDetailPanel {...props} />);

      expect(screen.getByText('Provenance')).toBeInTheDocument();
    });

    it('displays source_type from provenance', () => {
      const props = createDefaultProps();
      render(<MemoryDetailPanel {...props} />);

      expect(screen.getByText('session-extraction')).toBeInTheDocument();
    });

    it('displays session_id from provenance', () => {
      const props = createDefaultProps();
      render(<MemoryDetailPanel {...props} />);

      expect(screen.getByText('sess-abc123')).toBeInTheDocument();
    });

    it('displays shortened commit SHA', () => {
      const props = createDefaultProps();
      render(<MemoryDetailPanel {...props} />);

      // commit_sha is sliced to first 7 chars
      expect(screen.getByText('abc1234')).toBeInTheDocument();
    });

    it('displays files list joined by comma', () => {
      const props = createDefaultProps();
      render(<MemoryDetailPanel {...props} />);

      expect(
        screen.getByText('src/components/Button.tsx, src/components/Card.tsx')
      ).toBeInTheDocument();
    });

    it('shows "No provenance data available" when provenance is null', () => {
      const memory = createMockMemory({ provenance: null });
      const props = createDefaultProps({ memory });
      render(<MemoryDetailPanel {...props} />);

      expect(
        screen.getByText('No provenance data available')
      ).toBeInTheDocument();
    });
  });

  describe('Action callbacks', () => {
    it('calls onClose when close button is clicked', async () => {
      const user = userEvent.setup();
      const onClose = jest.fn();
      const props = createDefaultProps({ onClose });
      render(<MemoryDetailPanel {...props} />);

      const closeButton = screen.getByLabelText('Close detail panel');
      await user.click(closeButton);

      expect(onClose).toHaveBeenCalledTimes(1);
    });

    it('calls onClose when back button is clicked', async () => {
      const user = userEvent.setup();
      const onClose = jest.fn();
      const props = createDefaultProps({ onClose });
      render(<MemoryDetailPanel {...props} />);

      const backButton = screen.getByLabelText('Back to list');
      await user.click(backButton);

      expect(onClose).toHaveBeenCalledTimes(1);
    });

    it('calls onApprove when Approve button is clicked', async () => {
      const user = userEvent.setup();
      const onApprove = jest.fn();
      const props = createDefaultProps({ onApprove });
      render(<MemoryDetailPanel {...props} />);

      const approveButton = screen.getByRole('button', { name: /approve/i });
      await user.click(approveButton);

      expect(onApprove).toHaveBeenCalledWith('test-id-1');
    });

    it('calls onReject when Reject button is clicked', async () => {
      const user = userEvent.setup();
      const onReject = jest.fn();
      const props = createDefaultProps({ onReject });
      render(<MemoryDetailPanel {...props} />);

      const rejectButton = screen.getByRole('button', { name: /reject/i });
      await user.click(rejectButton);

      expect(onReject).toHaveBeenCalledWith('test-id-1');
    });

    it('calls onEdit when Edit button is clicked', async () => {
      const user = userEvent.setup();
      const onEdit = jest.fn();
      const props = createDefaultProps({ onEdit });
      render(<MemoryDetailPanel {...props} />);

      const editButton = screen.getByRole('button', { name: /edit/i });
      await user.click(editButton);

      expect(onEdit).toHaveBeenCalledWith('test-id-1');
    });

    it('calls onClose when Escape key is pressed', () => {
      const onClose = jest.fn();
      const props = createDefaultProps({ onClose, isOpen: true });
      render(<MemoryDetailPanel {...props} />);

      fireEvent.keyDown(document, { key: 'Escape' });

      expect(onClose).toHaveBeenCalledTimes(1);
    });

    it('does not call onClose on Escape when panel is closed', () => {
      const onClose = jest.fn();
      const props = createDefaultProps({ onClose, isOpen: false });
      render(<MemoryDetailPanel {...props} />);

      fireEvent.keyDown(document, { key: 'Escape' });

      expect(onClose).not.toHaveBeenCalled();
    });
  });

  describe('Accessibility', () => {
    it('has role="complementary"', () => {
      const props = createDefaultProps();
      render(<MemoryDetailPanel {...props} />);

      expect(screen.getByRole('complementary')).toBeInTheDocument();
    });

    it('has aria-label on the panel', () => {
      const props = createDefaultProps();
      render(<MemoryDetailPanel {...props} />);

      const panel = screen.getByRole('complementary');
      expect(panel).toHaveAttribute('aria-label', 'Memory detail panel');
    });

    it('has accessible confidence progressbar', () => {
      const props = createDefaultProps();
      render(<MemoryDetailPanel {...props} />);

      const progressbar = screen.getByRole('progressbar');
      expect(progressbar).toHaveAttribute('aria-valuemin', '0');
      expect(progressbar).toHaveAttribute('aria-valuemax', '100');
      expect(progressbar).toHaveAttribute('aria-valuenow', '87');
      expect(progressbar).toHaveAttribute('aria-label', 'Confidence: 87%');
    });
  });
});
