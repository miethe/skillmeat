'use client';

import { useState, useCallback } from 'react';
import Link from 'next/link';
import {
  Settings,
  Plus,
  ChevronRight,
  Search,
  Filter,
  ArrowUpDown,
  ChevronDown,
  Brain,
  ShieldAlert,
  GitBranch,
  Wrench,
  Puzzle,
  Lightbulb,
  Palette,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { cn } from '@/lib/utils';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const MEMORY_TYPES = [
  { value: 'all', label: 'All', icon: null },
  { value: 'constraint', label: 'Constraints', icon: ShieldAlert },
  { value: 'decision', label: 'Decisions', icon: GitBranch },
  { value: 'fix', label: 'Fixes', icon: Wrench },
  { value: 'pattern', label: 'Patterns', icon: Puzzle },
  { value: 'learning', label: 'Learnings', icon: Lightbulb },
  { value: 'style_rule', label: 'Style Rules', icon: Palette },
] as const;

const STATUS_OPTIONS = [
  { value: 'all', label: 'All Statuses' },
  { value: 'candidate', label: 'Candidate' },
  { value: 'active', label: 'Active' },
  { value: 'stable', label: 'Stable' },
  { value: 'deprecated', label: 'Deprecated' },
] as const;

const SORT_OPTIONS = [
  { value: 'newest', label: 'Newest First' },
  { value: 'oldest', label: 'Oldest First' },
  { value: 'confidence-desc', label: 'Highest Confidence' },
  { value: 'confidence-asc', label: 'Lowest Confidence' },
  { value: 'most-used', label: 'Most Used' },
] as const;

// ---------------------------------------------------------------------------
// Placeholder components (to be replaced in subsequent tasks)
// ---------------------------------------------------------------------------

/** Placeholder for the memory list. Accepts the same onSelect signature that
 *  the real MemoryList (UI-3.2) will use, so wiring is zero-effort later. */
function MemoryListPlaceholder(_props: { onSelect: (id: string | null) => void }) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-3 text-muted-foreground">
      <Brain className="h-12 w-12 opacity-30" />
      <p className="text-sm font-medium">Memory list will appear here</p>
      <p className="text-xs">Extracted knowledge items from AI sessions</p>
    </div>
  );
}

function DetailPanelPlaceholder() {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-3 text-muted-foreground">
      <p className="text-sm font-medium">Select a memory to view details</p>
      <p className="text-xs">Click on any memory item in the list</p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function getStatusLabel(value: string): string {
  return STATUS_OPTIONS.find((opt) => opt.value === value)?.label ?? 'All Statuses';
}

function getSortLabel(value: string): string {
  return SORT_OPTIONS.find((opt) => opt.value === value)?.label ?? 'Newest First';
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

interface MemoryPageContentProps {
  projectId: string;
}

export function MemoryPageContent({ projectId }: MemoryPageContentProps) {
  // ---------------------------------------------------------------------------
  // State
  // ---------------------------------------------------------------------------
  const [typeFilter, setTypeFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [sortBy, setSortBy] = useState('newest');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedMemoryId, setSelectedMemoryId] = useState<string | null>(null);

  // For now, use projectId as the display name. Hook integration comes in a
  // later task when useProject is wired up.
  const projectName = projectId;

  // Placeholder counts (will be replaced with real data from API queries)
  const counts: Record<string, number> = {
    all: 0,
    constraint: 0,
    decision: 0,
    fix: 0,
    pattern: 0,
    learning: 0,
    style_rule: 0,
  };

  const handleSearchChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchQuery(e.target.value);
  }, []);

  // Handler for selecting a memory item from the list. Passed to
  // MemoryListPlaceholder now and the real MemoryList in UI-3.2.
  const handleMemorySelect = useCallback((memoryId: string | null) => {
    setSelectedMemoryId(memoryId);
  }, []);

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------
  return (
    <div className="flex h-screen flex-col">
      {/* ------------------------------------------------------------------ */}
      {/* Page Header                                                        */}
      {/* ------------------------------------------------------------------ */}
      <div className="border-b px-6 pb-4 pt-6">
        {/* Breadcrumb */}
        <nav aria-label="Breadcrumb" className="mb-3">
          <ol className="flex items-center gap-1.5 text-sm text-muted-foreground">
            <li>
              <Link href="/projects" className="hover:text-foreground transition-colors">
                Projects
              </Link>
            </li>
            <li aria-hidden="true">
              <ChevronRight className="h-3.5 w-3.5" />
            </li>
            <li>
              <Link
                href={`/projects/${projectId}`}
                className="hover:text-foreground transition-colors"
              >
                {projectName}
              </Link>
            </li>
            <li aria-hidden="true">
              <ChevronRight className="h-3.5 w-3.5" />
            </li>
            <li className="font-medium text-foreground">Memory</li>
          </ol>
        </nav>

        {/* Title row */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Memory</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Review and manage extracted knowledge for this project
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm">
              <Settings className="mr-2 h-4 w-4" />
              Settings
            </Button>
            <Button size="sm">
              <Plus className="mr-2 h-4 w-4" />
              Create Memory
            </Button>
          </div>
        </div>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Type Tabs                                                          */}
      {/* ------------------------------------------------------------------ */}
      <div className="border-b px-6 py-2">
        <Tabs value={typeFilter} onValueChange={setTypeFilter}>
          <TabsList className="h-9 bg-transparent p-0" aria-label="Filter by memory type">
            {MEMORY_TYPES.map((type) => (
              <TabsTrigger
                key={type.value}
                value={type.value}
                className="data-[state=active]:bg-muted"
              >
                {type.icon && <type.icon className="mr-1.5 h-3.5 w-3.5" />}
                {type.label}
                <Badge variant="secondary" className="ml-1.5 px-1.5 py-0 text-[10px]">
                  {counts[type.value] ?? 0}
                </Badge>
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Filter / Controls Bar                                              */}
      {/* ------------------------------------------------------------------ */}
      <div className="flex items-center gap-3 border-b px-6 py-2" role="toolbar" aria-label="Memory filters">
        {/* Status filter */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" size="sm" className="h-8">
              <Filter className="mr-2 h-3.5 w-3.5" />
              {getStatusLabel(statusFilter)}
              <ChevronDown className="ml-2 h-3.5 w-3.5" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start">
            <DropdownMenuRadioGroup value={statusFilter} onValueChange={setStatusFilter}>
              {STATUS_OPTIONS.map((opt) => (
                <DropdownMenuRadioItem key={opt.value} value={opt.value}>
                  {opt.label}
                </DropdownMenuRadioItem>
              ))}
            </DropdownMenuRadioGroup>
          </DropdownMenuContent>
        </DropdownMenu>

        {/* Sort control */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" size="sm" className="h-8">
              <ArrowUpDown className="mr-2 h-3.5 w-3.5" />
              {getSortLabel(sortBy)}
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start">
            <DropdownMenuRadioGroup value={sortBy} onValueChange={setSortBy}>
              {SORT_OPTIONS.map((opt) => (
                <DropdownMenuRadioItem key={opt.value} value={opt.value}>
                  {opt.label}
                </DropdownMenuRadioItem>
              ))}
            </DropdownMenuRadioGroup>
          </DropdownMenuContent>
        </DropdownMenu>

        {/* Spacer */}
        <div className="flex-1" />

        {/* Search */}
        <div className="relative w-64">
          <Search className="pointer-events-none absolute left-2.5 top-2 h-3.5 w-3.5 text-muted-foreground" />
          <Input
            placeholder="Search memories..."
            value={searchQuery}
            onChange={handleSearchChange}
            className="h-8 pl-8 text-sm"
            aria-label="Search memories"
          />
        </div>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Main Content: List + Detail Panel                                  */}
      {/* ------------------------------------------------------------------ */}
      <div className="flex flex-1 overflow-hidden">
        {/* Memory list area (scrollable, flex-1) */}
        <div
          className="flex-1 overflow-y-auto"
          role="region"
          aria-label="Memory list"
        >
          {/* TODO: Replace with MemoryList in UI-3.2 */}
          <MemoryListPlaceholder onSelect={handleMemorySelect} />
        </div>

        {/* Detail panel (conditional, right sidebar) */}
        {selectedMemoryId && (
          <aside
            className={cn(
              'w-[420px] shrink-0 border-l overflow-y-auto',
              'hidden lg:block' // hide on smaller screens
            )}
            role="complementary"
            aria-label="Memory detail panel"
          >
            {/* TODO: Replace with DetailPanel in UI-3.4 */}
            <DetailPanelPlaceholder />
          </aside>
        )}
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Batch Action Bar (fixed bottom, conditional)                       */}
      {/* ------------------------------------------------------------------ */}
      {/* TODO: Replace with BatchActionBar component when batch selection is implemented */}
      <div
        className="hidden"
        role="toolbar"
        aria-label="Batch actions"
        data-placeholder="batch-action-bar"
      >
        {/* Batch action bar will appear here when items are selected */}
      </div>
    </div>
  );
}
