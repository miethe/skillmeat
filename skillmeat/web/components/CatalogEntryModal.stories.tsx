import type { Meta, StoryObj } from '@storybook/react';
import { CatalogEntryModal } from './CatalogEntryModal';
import type { CatalogEntry } from '@/types/marketplace';

const meta: Meta<typeof CatalogEntryModal> = {
  title: 'Components/CatalogEntryModal',
  component: CatalogEntryModal,
  parameters: {
    layout: 'centered',
  },
  tags: ['autodocs'],
  argTypes: {
    open: {
      control: 'boolean',
      description: 'Whether the modal is open',
    },
    onOpenChange: {
      action: 'onOpenChange',
      description: 'Callback when modal open state changes',
    },
    entry: {
      control: 'object',
      description: 'Catalog entry data to display',
    },
    onImport: {
      action: 'onImport',
      description: 'Callback when import button is clicked',
    },
    isImporting: {
      control: 'boolean',
      description: 'Whether an import is in progress',
    },
  },
};

export default meta;
type Story = StoryObj<typeof CatalogEntryModal>;

// Mock catalog entry with full data
const mockEntry: CatalogEntry = {
  id: 'cat_123',
  source_id: 'src_456',
  artifact_type: 'skill',
  name: 'canvas-design',
  path: 'skills/canvas-design',
  upstream_url: 'https://github.com/anthropics/skills/tree/main/canvas-design',
  detected_version: '1.2.0',
  detected_sha: 'abc123def456',
  detected_at: new Date('2024-01-15T10:30:00Z').toISOString(),
  confidence_score: 92,
  raw_score: 60,
  score_breakdown: {
    dir_name_score: 10,
    manifest_score: 20,
    extensions_score: 5,
    parent_hint_score: 15,
    frontmatter_score: 15,
    depth_penalty: -5,
    raw_total: 60,
    normalized_score: 92,
  },
  status: 'new',
};

/**
 * Default modal with full catalog entry data including score breakdown
 */
export const Default: Story = {
  args: {
    open: true,
    entry: mockEntry,
    isImporting: false,
  },
};

/**
 * Modal with catalog entry that doesn't have score breakdown data
 */
export const WithoutBreakdown: Story = {
  args: {
    open: true,
    entry: {
      ...mockEntry,
      score_breakdown: undefined,
    },
    isImporting: false,
  },
};

/**
 * Modal showing an entry that has already been imported
 */
export const ImportedStatus: Story = {
  args: {
    open: true,
    entry: {
      ...mockEntry,
      status: 'imported',
    },
    isImporting: false,
  },
};

/**
 * Modal showing an entry that has been removed from the source
 */
export const RemovedStatus: Story = {
  args: {
    open: true,
    entry: {
      ...mockEntry,
      status: 'removed',
    },
    isImporting: false,
  },
};

/**
 * Modal in importing state with loading spinner
 */
export const Importing: Story = {
  args: {
    open: true,
    entry: mockEntry,
    isImporting: true,
  },
};

/**
 * Modal showing an entry with low confidence score
 */
export const LowConfidence: Story = {
  args: {
    open: true,
    entry: {
      ...mockEntry,
      confidence_score: 45,
      raw_score: 30,
      score_breakdown: {
        dir_name_score: 5,
        manifest_score: 0,
        extensions_score: 5,
        parent_hint_score: 10,
        frontmatter_score: 0,
        depth_penalty: -10,
        raw_total: 10,
        normalized_score: 45,
      },
    },
    isImporting: false,
  },
};

/**
 * Modal showing an MCP server artifact type
 */
export const McpServerType: Story = {
  args: {
    open: true,
    entry: {
      ...mockEntry,
      artifact_type: 'mcp-server',
      name: 'filesystem-mcp',
      path: 'mcp/filesystem',
      confidence_score: 88,
      raw_score: 55,
      score_breakdown: {
        dir_name_score: 10,
        manifest_score: 15,
        extensions_score: 10,
        parent_hint_score: 10,
        frontmatter_score: 10,
        depth_penalty: 0,
        raw_total: 55,
        normalized_score: 88,
      },
    },
    isImporting: false,
  },
};

/**
 * Modal showing a command artifact type
 */
export const CommandType: Story = {
  args: {
    open: true,
    entry: {
      ...mockEntry,
      artifact_type: 'command',
      name: 'git-commit',
      path: 'commands/git-commit',
      confidence_score: 95,
      raw_score: 65,
      score_breakdown: {
        dir_name_score: 10,
        manifest_score: 25,
        extensions_score: 5,
        parent_hint_score: 15,
        frontmatter_score: 15,
        depth_penalty: -5,
        raw_total: 65,
        normalized_score: 95,
      },
    },
    isImporting: false,
  },
};

/**
 * Modal showing an entry without a detected version
 */
export const NoVersion: Story = {
  args: {
    open: true,
    entry: {
      ...mockEntry,
      detected_version: null,
    },
    isImporting: false,
  },
};

/**
 * Modal showing a very long path
 */
export const LongPath: Story = {
  args: {
    open: true,
    entry: {
      ...mockEntry,
      path: 'very/deeply/nested/directory/structure/with/many/levels/skills/canvas-design',
    },
    isImporting: false,
  },
};

/**
 * Modal in closed state (for testing transitions)
 */
export const Closed: Story = {
  args: {
    open: false,
    entry: mockEntry,
    isImporting: false,
  },
};
