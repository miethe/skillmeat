'use client';

import * as React from 'react';
import { Wrench, X, Check, Search } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { cn } from '@/lib/utils';
import { Tool } from '@/types/enums';

interface AvailableTool {
  name: string;
  artifact_count: number;
}

interface ToolFilterPopoverProps {
  selectedTools: string[];
  onChange: (tools: string[]) => void;
  /** Optional: If provided, use these tools instead of static list */
  availableTools?: AvailableTool[];
  className?: string;
}

// Known Claude Code tools from the enum
const KNOWN_TOOLS = [
  Tool.ASK_USER_QUESTION,
  Tool.BASH,
  Tool.EDIT,
  Tool.ENTER_PLAN_MODE,
  Tool.EXIT_PLAN_MODE,
  Tool.GLOB,
  Tool.GREP,
  Tool.KILL_SHELL,
  Tool.MULTI_EDIT,
  Tool.NOTEBOOK_EDIT,
  Tool.READ,
  Tool.SKILL,
  Tool.TASK,
  Tool.TASK_OUTPUT,
  Tool.TODO_WRITE,
  Tool.WEB_FETCH,
  Tool.WEB_SEARCH,
  Tool.WRITE,
] as const;

/**
 * Tool filter popover component with search and multi-select
 *
 * Shows a popover with all available Claude Code tools and their artifact counts.
 * Allows multi-select of tools for filtering with a search box.
 *
 * @example
 * ```tsx
 * const [selectedTools, setSelectedTools] = useState<string[]>([]);
 * <ToolFilterPopover selectedTools={selectedTools} onChange={setSelectedTools} />
 * ```
 */
export function ToolFilterPopover({
  selectedTools,
  onChange,
  availableTools,
  className,
}: ToolFilterPopoverProps) {
  const [open, setOpen] = React.useState(false);
  const [search, setSearch] = React.useState('');

  // Use provided tools or fall back to known tools list
  const tools = React.useMemo(() => {
    if (availableTools) {
      return availableTools;
    }
    // Convert known tools to AvailableTool format with 0 count
    return KNOWN_TOOLS.map((tool) => ({
      name: tool,
      artifact_count: 0,
    }));
  }, [availableTools]);

  // Filter tools by search
  const filteredTools = React.useMemo(() => {
    if (!search) return tools;
    return tools.filter((tool) => tool.name.toLowerCase().includes(search.toLowerCase()));
  }, [tools, search]);

  // Toggle tool by name
  const toggleTool = (toolName: string) => {
    if (selectedTools.includes(toolName)) {
      onChange(selectedTools.filter((name) => name !== toolName));
    } else {
      onChange([...selectedTools, toolName]);
    }
  };

  const clearAll = () => {
    onChange([]);
    setSearch('');
  };

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button variant="outline" size="sm" className={cn('gap-2', className)}>
          <Wrench className="h-4 w-4" />
          Tools
          {selectedTools.length > 0 && (
            <Badge variant="secondary" className="ml-1 rounded-full px-2">
              {selectedTools.length}
            </Badge>
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-72 p-0" align="start">
        <div className="border-b p-3">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-sm font-medium">Filter by tools</span>
            {selectedTools.length > 0 && (
              <Button variant="ghost" size="sm" onClick={clearAll} className="h-6 px-2 text-xs">
                Clear all
              </Button>
            )}
          </div>
          <div className="relative">
            <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search tools..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="h-9 pl-8"
            />
          </div>
        </div>
        <ScrollArea className="h-60">
          <div className="p-2">
            {filteredTools.length === 0 ? (
              <div className="py-4 text-center text-sm text-muted-foreground">No tools found</div>
            ) : (
              filteredTools.map((tool) => {
                const isSelected = selectedTools.includes(tool.name);
                return (
                  <div
                    key={tool.name}
                    className={cn(
                      'flex cursor-pointer items-center justify-between rounded-md px-2 py-1.5 hover:bg-accent',
                      isSelected && 'bg-accent'
                    )}
                    onClick={() => toggleTool(tool.name)}
                  >
                    <div className="flex items-center gap-2">
                      <div
                        className={cn(
                          'flex h-4 w-4 items-center justify-center rounded border',
                          isSelected ? 'border-primary bg-primary' : 'border-input'
                        )}
                      >
                        {isSelected && <Check className="h-3 w-3 text-primary-foreground" />}
                      </div>
                      <span className="text-sm font-mono">{tool.name}</span>
                    </div>
                    {tool.artifact_count > 0 && (
                      <span className="text-xs text-muted-foreground">{tool.artifact_count}</span>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </ScrollArea>
      </PopoverContent>
    </Popover>
  );
}

/**
 * Inline filter bar showing selected tools with remove buttons
 *
 * Only visible when tools are selected. Shows each selected tool
 * with an X button to remove it, plus a "Clear all" button.
 *
 * @example
 * ```tsx
 * const [selectedTools, setSelectedTools] = useState<string[]>(['Read', 'Write']);
 * <ToolFilterBar selectedTools={selectedTools} onChange={setSelectedTools} />
 * ```
 */
export function ToolFilterBar({
  selectedTools,
  onChange,
  className,
}: {
  selectedTools: string[];
  onChange: (tools: string[]) => void;
  className?: string;
}) {
  if (selectedTools.length === 0) return null;

  return (
    <div className={cn('flex flex-wrap items-center gap-2', className)}>
      <span className="text-sm text-muted-foreground">Tools:</span>
      {selectedTools.map((toolName) => (
        <Badge key={toolName} variant="secondary" className="gap-1 font-mono">
          {toolName}
          <X
            className="h-3 w-3 cursor-pointer hover:opacity-70"
            onClick={() => onChange(selectedTools.filter((name) => name !== toolName))}
          />
        </Badge>
      ))}
      <Button variant="ghost" size="sm" onClick={() => onChange([])} className="h-6 text-xs">
        Clear all
      </Button>
    </div>
  );
}
