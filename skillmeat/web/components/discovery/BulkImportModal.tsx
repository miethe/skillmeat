'use client';

import { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Badge } from '@/components/ui/badge';
import { Loader2, Pencil, Package } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

/**
 * Discovered artifact from local filesystem
 */
export interface DiscoveredArtifact {
  type: string;
  name: string;
  source?: string;
  version?: string;
  scope?: string;
  tags?: string[];
  description?: string;
  path: string;
  discovered_at: string;
}

export interface BulkImportModalProps {
  artifacts: DiscoveredArtifact[];
  open: boolean;
  onClose: () => void;
  onImport: (selected: DiscoveredArtifact[]) => Promise<void>;
}

export function BulkImportModal({ artifacts, open, onClose, onImport }: BulkImportModalProps) {
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [isImporting, setIsImporting] = useState(false);
  const { toast } = useToast();

  const isAllSelected = artifacts.length > 0 && selected.size === artifacts.length;
  const isPartiallySelected = selected.size > 0 && selected.size < artifacts.length;

  const toggleSelectAll = () => {
    if (isAllSelected) {
      setSelected(new Set());
    } else {
      setSelected(new Set(artifacts.map((a) => a.path)));
    }
  };

  const toggleSelect = (path: string) => {
    const newSelected = new Set(selected);
    if (newSelected.has(path)) {
      newSelected.delete(path);
    } else {
      newSelected.add(path);
    }
    setSelected(newSelected);
  };

  const handleImport = async () => {
    if (selected.size === 0) return;

    setIsImporting(true);
    try {
      const selectedArtifacts = artifacts.filter((a) => selected.has(a.path));
      await onImport(selectedArtifacts);

      toast({
        title: 'Import successful',
        description: `Successfully imported ${selected.size} artifact${selected.size > 1 ? 's' : ''}`,
      });

      // Reset state and close
      setSelected(new Set());
      onClose();
    } catch (error) {
      console.error('Import failed:', error);
      toast({
        title: 'Import failed',
        description: error instanceof Error ? error.message : 'An error occurred during import',
        variant: 'destructive',
      });
    } finally {
      setIsImporting(false);
    }
  };

  const handleClose = () => {
    if (!isImporting) {
      setSelected(new Set());
      onClose();
    }
  };

  const handleEdit = (artifact: DiscoveredArtifact) => {
    // TODO: Implement parameter editor
    console.log('Edit artifact:', artifact);
  };

  return (
    <Dialog open={open} onOpenChange={(open) => !open && handleClose()}>
      <DialogContent className="sm:max-w-[900px] max-h-[80vh] flex flex-col">
        <DialogHeader>
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-primary/10 p-2">
              <Package className="h-5 w-5 text-primary" />
            </div>
            <div>
              <DialogTitle>Review Discovered Artifacts</DialogTitle>
              <DialogDescription>
                Select artifacts to import into your collection ({artifacts.length} discovered)
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <div className="flex-1 overflow-auto border rounded-md">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-12">
                  <Checkbox
                    checked={isAllSelected}
                    onCheckedChange={toggleSelectAll}
                    aria-label="Select all artifacts"
                    data-indeterminate={isPartiallySelected}
                  />
                </TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Name</TableHead>
                <TableHead>Version</TableHead>
                <TableHead className="min-w-[200px]">Source</TableHead>
                <TableHead>Tags</TableHead>
                <TableHead className="w-20">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {artifacts.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center text-muted-foreground py-8">
                    No artifacts discovered
                  </TableCell>
                </TableRow>
              ) : (
                artifacts.map((artifact) => (
                  <TableRow
                    key={artifact.path}
                    data-state={selected.has(artifact.path) ? 'selected' : undefined}
                    className="cursor-pointer"
                    onClick={() => toggleSelect(artifact.path)}
                  >
                    <TableCell onClick={(e) => e.stopPropagation()}>
                      <Checkbox
                        checked={selected.has(artifact.path)}
                        onCheckedChange={() => toggleSelect(artifact.path)}
                        aria-label={`Select ${artifact.name}`}
                      />
                    </TableCell>
                    <TableCell>
                      <Badge variant="secondary">{artifact.type}</Badge>
                    </TableCell>
                    <TableCell className="font-medium">{artifact.name}</TableCell>
                    <TableCell>
                      <code className="text-xs bg-muted px-1.5 py-0.5 rounded">
                        {artifact.version || '—'}
                      </code>
                    </TableCell>
                    <TableCell>
                      <span className="font-mono text-xs truncate block max-w-[200px]" title={artifact.source}>
                        {artifact.source || '—'}
                      </span>
                    </TableCell>
                    <TableCell>
                      {artifact.tags && artifact.tags.length > 0 ? (
                        <span className="text-xs text-muted-foreground">
                          {artifact.tags.join(', ')}
                        </span>
                      ) : (
                        <span className="text-xs text-muted-foreground">—</span>
                      )}
                    </TableCell>
                    <TableCell onClick={(e) => e.stopPropagation()}>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleEdit(artifact)}
                        disabled={isImporting}
                        aria-label={`Edit ${artifact.name}`}
                      >
                        <Pencil className="h-4 w-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>

        <DialogFooter>
          <div className="flex items-center justify-between w-full">
            <div className="text-sm text-muted-foreground">
              {selected.size > 0 && `${selected.size} selected`}
            </div>
            <div className="flex gap-2">
              <Button variant="outline" onClick={handleClose} disabled={isImporting}>
                Cancel
              </Button>
              <Button onClick={handleImport} disabled={selected.size === 0 || isImporting}>
                {isImporting ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Importing...
                  </>
                ) : (
                  `Import ${selected.size > 0 ? `(${selected.size})` : ''}`
                )}
              </Button>
            </div>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
