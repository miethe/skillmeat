/**
 * Template Card Component
 *
 * Displays a project template in a card format with name, description,
 * entity count, collection badge, and action buttons for preview and deploy.
 *
 * Visual design follows unified card patterns with hover effects and
 * accessible controls.
 */

'use client';

import * as React from 'react';
import { Eye, Rocket, Package } from 'lucide-react';
import { Card, CardHeader, CardContent, CardFooter } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

// ============================================================================
// Types
// ============================================================================

/**
 * Template data structure matching backend ProjectTemplateResponse
 */
export interface Template {
  /** Unique identifier for the template */
  id: string;
  /** Template name */
  name: string;
  /** Optional template description */
  description: string | null;
  /** Number of entities in the template */
  entity_count: number;
  /** Optional source collection ID */
  collection_id: string | null;
}

export interface TemplateCardProps {
  /** The template to display */
  template: Template;
  /** Callback when preview button is clicked */
  onPreview?: (template: Template) => void;
  /** Callback when deploy button is clicked */
  onDeploy?: (template: Template) => void;
}

// ============================================================================
// Main Component
// ============================================================================

/**
 * TemplateCard - Card for displaying a project template
 *
 * Shows template information including name, description (truncated to 2 lines),
 * entity count, optional collection badge, and action buttons for preview and deploy.
 *
 * Visual design:
 * - Card container with hover effect (shadow and slight scale)
 * - Prominent template name as title
 * - Description truncated with line-clamp-2
 * - Entity count badge and optional collection badge
 * - Two action buttons at footer: Preview (ghost) and Deploy (default/primary)
 *
 * @example
 * ```tsx
 * <TemplateCard
 *   template={{
 *     id: 'tpl_123',
 *     name: 'FastAPI + Next.js',
 *     description: 'Complete setup for modern web apps with API backend',
 *     entity_count: 9,
 *     collection_id: 'col_456',
 *   }}
 *   onPreview={(template) => openPreviewModal(template)}
 *   onDeploy={(template) => openDeployWizard(template)}
 * />
 * ```
 *
 * @param props - TemplateCardProps configuration
 * @returns Card component with template information and actions
 */
export function TemplateCard({ template, onPreview, onDeploy }: TemplateCardProps) {
  const handlePreview = (e: React.MouseEvent) => {
    e.stopPropagation();
    onPreview?.(template);
  };

  const handleDeploy = (e: React.MouseEvent) => {
    e.stopPropagation();
    onDeploy?.(template);
  };

  return (
    <Card
      className={cn(
        'group relative',
        'transition-all duration-200',
        'hover:scale-[1.02] hover:shadow-md',
        'flex h-full flex-col'
      )}
      role="article"
      aria-label={`Template: ${template.name}`}
    >
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-2">
          <h3 className="text-lg font-semibold leading-tight">{template.name}</h3>
          <Package className="h-5 w-5 flex-shrink-0 text-muted-foreground" />
        </div>
      </CardHeader>

      <CardContent className="flex-1 pb-3">
        {/* Description (truncated to 2 lines) */}
        {template.description && (
          <p className="mb-3 line-clamp-2 text-sm text-muted-foreground">{template.description}</p>
        )}

        {/* Badges: Entity count and optional collection */}
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="secondary" className="gap-1 text-xs">
            <span className="font-semibold">{template.entity_count}</span>
            {template.entity_count === 1 ? 'entity' : 'entities'}
          </Badge>

          {template.collection_id && (
            <Badge variant="outline" className="text-xs">
              collection
            </Badge>
          )}
        </div>
      </CardContent>

      <CardFooter className="border-t pt-3">
        <div className="flex w-full items-center justify-end gap-2">
          {onPreview && (
            <Button variant="ghost" size="sm" onClick={handlePreview} aria-label="Preview template">
              <Eye className="mr-1 h-4 w-4" />
              Preview
            </Button>
          )}
          {onDeploy && (
            <Button variant="default" size="sm" onClick={handleDeploy} aria-label="Deploy template">
              <Rocket className="mr-1 h-4 w-4" />
              Deploy
            </Button>
          )}
        </div>
      </CardFooter>
    </Card>
  );
}
