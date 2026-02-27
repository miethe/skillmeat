/**
 * @jest-environment jsdom
 *
 * Tests for LogViewer component.
 *
 * Focus areas:
 *   - Empty state renders "Waiting for logs..." message
 *   - Renders log lines with their messages
 *   - Error lines (level='error') have error styling class
 *   - Warning lines (level='warn') have warning styling class
 *   - Debug lines (level='debug') have muted styling class
 *   - Line numbers rendered when showLineNumbers=true (default)
 *   - Line numbers hidden when showLineNumbers=false
 *   - Timestamps rendered when provided
 *   - Container has role="log" and aria-live="polite"
 *   - Message-token detection: [ERROR]/[FATAL] → error styling, [WARN] → warn
 */

import { render, screen, within } from '@testing-library/react';
import { LogViewer } from '@/components/workflow/log-viewer';
import type { LogLine } from '@/components/workflow/log-viewer';

// ============================================================================
// Fixture factory
// ============================================================================

function makeLine(overrides: Partial<LogLine> = {}): LogLine {
  return {
    message: 'Default log message',
    ...overrides,
  };
}

// ============================================================================
// Empty state
// ============================================================================

describe('LogViewer — empty state', () => {
  it('renders "Waiting for logs..." when lines array is empty', () => {
    render(<LogViewer lines={[]} />);
    expect(screen.getByText(/Waiting for logs/i)).toBeInTheDocument();
  });

  it('does not render any log line rows when empty', () => {
    const { container } = render(<LogViewer lines={[]} />);
    // No lines to render; the message span should be the only content
    const logContainer = container.querySelector('[role="log"]');
    expect(logContainer).toBeInTheDocument();
    expect(screen.queryByText('1')).not.toBeInTheDocument(); // no line number "1"
  });
});

// ============================================================================
// Accessibility — role and aria attributes
// ============================================================================

describe('LogViewer — accessibility attributes', () => {
  it('has role="log" on the container', () => {
    render(<LogViewer lines={[]} />);
    expect(screen.getByRole('log')).toBeInTheDocument();
  });

  it('has aria-live="polite" on the container', () => {
    render(<LogViewer lines={[]} />);
    const container = screen.getByRole('log');
    expect(container).toHaveAttribute('aria-live', 'polite');
  });

  it('has aria-label="Stage execution logs"', () => {
    render(<LogViewer lines={[]} />);
    expect(screen.getByLabelText('Stage execution logs')).toBeInTheDocument();
  });

  it('has aria-atomic="false" on the container', () => {
    render(<LogViewer lines={[]} />);
    const container = screen.getByRole('log');
    expect(container).toHaveAttribute('aria-atomic', 'false');
  });
});

// ============================================================================
// Log line rendering
// ============================================================================

describe('LogViewer — log line rendering', () => {
  it('renders log lines with their message text', () => {
    const lines: LogLine[] = [
      makeLine({ message: 'Starting build...' }),
      makeLine({ message: 'Compiling source files' }),
      makeLine({ message: 'Build successful' }),
    ];
    render(<LogViewer lines={lines} />);
    expect(screen.getByText('Starting build...')).toBeInTheDocument();
    expect(screen.getByText('Compiling source files')).toBeInTheDocument();
    expect(screen.getByText('Build successful')).toBeInTheDocument();
  });

  it('renders all provided log lines', () => {
    const lines = Array.from({ length: 5 }, (_, i) =>
      makeLine({ message: `Line ${i + 1}` })
    );
    render(<LogViewer lines={lines} />);
    for (let i = 1; i <= 5; i++) {
      expect(screen.getByText(`Line ${i}`)).toBeInTheDocument();
    }
  });
});

// ============================================================================
// Line numbers
// ============================================================================

describe('LogViewer — line numbers', () => {
  it('shows line numbers by default (showLineNumbers defaults to true)', () => {
    const lines = [makeLine({ message: 'First line' }), makeLine({ message: 'Second line' })];
    render(<LogViewer lines={lines} />);
    // Line number "1" and "2" should appear as aria-hidden spans
    // They are aria-hidden but visible in the DOM
    const log = screen.getByRole('log');
    expect(within(log).getByText('1')).toBeInTheDocument();
    expect(within(log).getByText('2')).toBeInTheDocument();
  });

  it('shows line numbers when showLineNumbers=true', () => {
    const lines = [makeLine({ message: 'Hello' })];
    render(<LogViewer lines={lines} showLineNumbers={true} />);
    const log = screen.getByRole('log');
    expect(within(log).getByText('1')).toBeInTheDocument();
  });

  it('does not show line numbers when showLineNumbers=false', () => {
    const lines = [makeLine({ message: 'No numbers here' }), makeLine({ message: 'Or here' })];
    render(<LogViewer lines={lines} showLineNumbers={false} />);
    const log = screen.getByRole('log');
    expect(within(log).queryByText('1')).not.toBeInTheDocument();
    expect(within(log).queryByText('2')).not.toBeInTheDocument();
  });
});

// ============================================================================
// Error line styling
// ============================================================================

describe('LogViewer — error line styling', () => {
  it('applies error styling for lines with level="error"', () => {
    const lines = [makeLine({ message: 'Something broke', level: 'error' })];
    const { container } = render(<LogViewer lines={lines} />);
    // The row element should have the red error class
    const row = container.querySelector('.bg-red-500\\/10');
    expect(row).toBeInTheDocument();
    expect(row).toHaveTextContent('Something broke');
  });

  it('applies error styling for lines with [ERROR] token in message', () => {
    const lines = [makeLine({ message: '[ERROR] Connection refused' })];
    const { container } = render(<LogViewer lines={lines} />);
    const row = container.querySelector('.bg-red-500\\/10');
    expect(row).toBeInTheDocument();
  });

  it('applies error styling for lines with [FATAL] token in message', () => {
    const lines = [makeLine({ message: '[FATAL] Out of memory' })];
    const { container } = render(<LogViewer lines={lines} />);
    const row = container.querySelector('.bg-red-500\\/10');
    expect(row).toBeInTheDocument();
  });
});

// ============================================================================
// Warning line styling
// ============================================================================

describe('LogViewer — warning line styling', () => {
  it('applies warning styling for lines with level="warn"', () => {
    const lines = [makeLine({ message: 'Deprecated API usage', level: 'warn' })];
    const { container } = render(<LogViewer lines={lines} />);
    // Warning rows use text-amber-500 class
    const row = container.querySelector('.text-amber-500');
    expect(row).toBeInTheDocument();
    expect(row).toHaveTextContent('Deprecated API usage');
  });

  it('applies warning styling for lines with [WARN] token in message', () => {
    const lines = [makeLine({ message: '[WARN] Slow query detected' })];
    const { container } = render(<LogViewer lines={lines} />);
    const row = container.querySelector('.text-amber-500');
    expect(row).toBeInTheDocument();
  });
});

// ============================================================================
// Debug line styling
// ============================================================================

describe('LogViewer — debug line styling', () => {
  it('applies debug/muted styling for lines with level="debug"', () => {
    const lines = [makeLine({ message: 'Debug trace info', level: 'debug' })];
    const { container } = render(<LogViewer lines={lines} />);
    // Debug lines use text-muted-foreground/60 class
    const row = container.querySelector('.text-muted-foreground\\/60');
    expect(row).toBeInTheDocument();
    expect(row).toHaveTextContent('Debug trace info');
  });
});

// ============================================================================
// Info line styling
// ============================================================================

describe('LogViewer — info / default line styling', () => {
  it('renders info lines without special coloring class', () => {
    const lines = [makeLine({ message: 'Normal info message', level: 'info' })];
    const { container } = render(<LogViewer lines={lines} />);
    // Should not have error or warning classes
    expect(container.querySelector('.bg-red-500\\/10')).not.toBeInTheDocument();
    expect(container.querySelector('.text-amber-500')).not.toBeInTheDocument();
  });

  it('does not apply error/warn styling to lines without level or tokens', () => {
    const lines = [makeLine({ message: 'Just a plain log line' })];
    const { container } = render(<LogViewer lines={lines} />);
    expect(container.querySelector('.bg-red-500\\/10')).not.toBeInTheDocument();
    expect(container.querySelector('.text-amber-500')).not.toBeInTheDocument();
  });

  it('explicit level takes precedence over message tokens', () => {
    // Message has [WARN] but level is 'error' — should get error styling
    const lines = [makeLine({ message: '[WARN] Actually an error', level: 'error' })];
    const { container } = render(<LogViewer lines={lines} />);
    const errorRow = container.querySelector('.bg-red-500\\/10');
    expect(errorRow).toBeInTheDocument();
  });
});

// ============================================================================
// Timestamps
// ============================================================================

describe('LogViewer — timestamps', () => {
  it('renders timestamp when provided on a line', () => {
    const lines = [makeLine({ message: 'Timestamped event', timestamp: '10:30:45' })];
    render(<LogViewer lines={lines} />);
    expect(screen.getByText('[10:30:45]')).toBeInTheDocument();
  });

  it('does not render timestamp when absent on a line', () => {
    const lines = [makeLine({ message: 'No timestamp here' })];
    render(<LogViewer lines={lines} />);
    // No bracket-wrapped text matching a timestamp pattern
    expect(screen.queryByText(/\[\d{2}:\d{2}:\d{2}\]/)).not.toBeInTheDocument();
  });

  it('renders timestamps for multiple lines independently', () => {
    const lines: LogLine[] = [
      { message: 'First', timestamp: '10:00:01' },
      { message: 'Second' },
      { message: 'Third', timestamp: '10:00:03' },
    ];
    render(<LogViewer lines={lines} />);
    expect(screen.getByText('[10:00:01]')).toBeInTheDocument();
    expect(screen.getByText('[10:00:03]')).toBeInTheDocument();
  });
});

// ============================================================================
// maxHeight prop
// ============================================================================

describe('LogViewer — maxHeight prop', () => {
  it('applies custom maxHeight via inline style on the scrollable viewport', () => {
    const { container } = render(
      <LogViewer lines={[]} maxHeight="40rem" />
    );
    const viewport = container.querySelector('[style*="max-height"]');
    expect(viewport).toHaveStyle({ maxHeight: '40rem' });
  });

  it('defaults to "24rem" maxHeight', () => {
    const { container } = render(<LogViewer lines={[]} />);
    const viewport = container.querySelector('[style*="max-height"]');
    expect(viewport).toHaveStyle({ maxHeight: '24rem' });
  });
});

// ============================================================================
// Mixed level lines
// ============================================================================

describe('LogViewer — mixed severity lines', () => {
  it('renders each line with correct severity independently', () => {
    const lines: LogLine[] = [
      { message: 'Normal line' },
      { message: 'Error line', level: 'error' },
      { message: 'Warning line', level: 'warn' },
      { message: 'Debug line', level: 'debug' },
    ];
    const { container } = render(<LogViewer lines={lines} showLineNumbers={false} />);
    expect(screen.getByText('Normal line')).toBeInTheDocument();
    expect(screen.getByText('Error line')).toBeInTheDocument();
    expect(screen.getByText('Warning line')).toBeInTheDocument();
    expect(screen.getByText('Debug line')).toBeInTheDocument();
    // Exactly one error row
    expect(container.querySelectorAll('.bg-red-500\\/10')).toHaveLength(1);
    // Exactly one amber warning row
    expect(container.querySelectorAll('.text-amber-500')).toHaveLength(1);
  });
});
