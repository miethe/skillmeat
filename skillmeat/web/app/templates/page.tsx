'use client';

import { useState } from 'react';
import { Plus, Package, Loader2, Search } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';

// Import template components
import { TemplateCard } from '@/components/templates/template-card';
import { TemplateDetail } from '@/components/templates/template-detail';
import { TemplateDeployWizard } from '@/components/templates/template-deploy-wizard';

// Import hooks
import { useTemplates, useToast } from '@/hooks';

// Import types
import type { ProjectTemplate, TemplateFilters } from '@/types/template';

// Deployment result type matching the wizard's internal type
interface DeploymentResult {
  success: boolean;
  message?: string;
  deployed_files?: Array<{ path: string; status: string; message?: string }>;
  errors?: string[];
}

function EmptyState({ hasFilters }: { hasFilters: boolean }) {
  return (
    <div className="flex h-full items-center justify-center py-12">
      <div className="text-center">
        <Package className="mx-auto h-12 w-12 text-muted-foreground/50" />
        <h3 className="mt-4 text-lg font-semibold">
          {hasFilters ? 'No templates match filters' : 'No templates available'}
        </h3>
        <p className="mt-2 text-sm text-muted-foreground">
          {hasFilters
            ? "Try adjusting your search to find what you're looking for."
            : 'Create your first template or import from the marketplace.'}
        </p>
      </div>
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
      {[...Array(6)].map((_, i) => (
        <div key={i} className="space-y-3 rounded-lg border p-4">
          <div className="flex items-start justify-between">
            <Skeleton className="h-6 w-3/4" />
            <Skeleton className="h-5 w-5 rounded" />
          </div>
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-2/3" />
          <div className="flex gap-2 pt-2">
            <Skeleton className="h-6 w-20" />
            <Skeleton className="h-6 w-16" />
          </div>
          <div className="flex justify-end gap-2 pt-3">
            <Skeleton className="h-8 w-20" />
            <Skeleton className="h-8 w-20" />
          </div>
        </div>
      ))}
    </div>
  );
}

export default function TemplatesPage() {
  const { toast } = useToast();

  // Filter state
  const [searchQuery, setSearchQuery] = useState('');
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [filters, _setFilters] = useState<TemplateFilters>({});

  // Modal state
  const [selectedTemplate, setSelectedTemplate] = useState<ProjectTemplate | null>(null);
  const [isDetailOpen, setIsDetailOpen] = useState(false);
  const [isDeployOpen, setIsDeployOpen] = useState(false);

  // Data fetching with cursor-based pagination
  const [paginationCursor, setPaginationCursor] = useState<string | undefined>(undefined);
  const {
    data,
    isLoading,
    error,
    // refetch available for pull-to-refresh if needed
  } = useTemplates({ ...filters, search: searchQuery || undefined, after: paginationCursor });

  // Event handlers
  const handlePreview = (template: ProjectTemplate) => {
    setSelectedTemplate(template);
    setIsDetailOpen(true);
  };

  const handleDetailClose = () => {
    setIsDetailOpen(false);
    setTimeout(() => setSelectedTemplate(null), 300);
  };

  const handleDeploy = (template: ProjectTemplate) => {
    setSelectedTemplate(template);
    setIsDeployOpen(true);
  };

  const handleDeploySuccess = (result: DeploymentResult) => {
    setIsDeployOpen(false);
    toast({
      title: 'Template deployed',
      description: result.message || `Template deployed successfully`,
    });
  };

  const handleLoadMore = () => {
    if (data?.page_info.end_cursor) {
      setPaginationCursor(data.page_info.end_cursor);
    }
  };

  const handleSearch = (value: string) => {
    setSearchQuery(value);
    setPaginationCursor(undefined); // Reset pagination when search changes
  };

  // Determine if filters are active
  const hasActiveFilters = !!searchQuery;

  return (
    <div className="space-y-6 p-6">
      {/* Page Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-3xl font-bold tracking-tight">Project Templates</h1>
          <p className="text-muted-foreground">
            Start new projects quickly with pre-configured context entities
          </p>
        </div>
        <Button disabled>
          <Plus className="mr-2 h-4 w-4" />
          Create Template
        </Button>
      </div>

      {/* Search Bar */}
      <div className="flex gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search templates..."
            value={searchQuery}
            onChange={(e) => handleSearch(e.target.value)}
            className="pl-9"
          />
        </div>
      </div>

      {/* Main Content */}
      <div className="space-y-4">
        {/* Results Header */}
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">
            {isLoading ? (
              <Skeleton className="h-6 w-32" />
            ) : error ? (
              'Error loading templates'
            ) : (
              <>
                {data?.items.length || 0}{' '}
                {data?.items.length === 1 ? 'Template' : 'Templates'}
              </>
            )}
          </h2>
        </div>

        {/* Error State */}
        {error && (
          <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4">
            <p className="text-sm text-destructive">
              Failed to load templates. Please try again later.
            </p>
            <p className="mt-1 text-xs text-destructive/80">
              {error instanceof Error ? error.message : 'Unknown error'}
            </p>
          </div>
        )}

        {/* Loading State */}
        {isLoading && <LoadingSkeleton />}

        {/* Empty State */}
        {!isLoading && !error && (!data?.items || data.items.length === 0) && (
          <EmptyState hasFilters={hasActiveFilters} />
        )}

        {/* Templates Grid */}
        {!isLoading && !error && data?.items && data.items.length > 0 && (
          <>
            <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
              {data.items.map((template) => (
                <TemplateCard
                  key={template.id}
                  template={template}
                  onPreview={() => handlePreview(template)}
                  onDeploy={() => handleDeploy(template)}
                />
              ))}
            </div>

            {/* Load More Button */}
            {data.page_info.has_next_page && (
              <div className="flex justify-center pt-6">
                <Button
                  variant="outline"
                  onClick={handleLoadMore}
                  disabled={isLoading}
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Loading...
                    </>
                  ) : (
                    'Load More'
                  )}
                </Button>
              </div>
            )}
          </>
        )}
      </div>

      {/* Detail Modal */}
      {selectedTemplate && (
        <TemplateDetail
          template={selectedTemplate}
          open={isDetailOpen}
          onOpenChange={setIsDetailOpen}
          onDeploy={() => {
            handleDetailClose();
            handleDeploy(selectedTemplate);
          }}
        />
      )}

      {/* Deploy Wizard */}
      {selectedTemplate && (
        <TemplateDeployWizard
          template={selectedTemplate}
          open={isDeployOpen}
          onOpenChange={setIsDeployOpen}
          onSuccess={handleDeploySuccess}
        />
      )}
    </div>
  );
}
