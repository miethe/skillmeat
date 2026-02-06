import Link from 'next/link';
import { ChevronLeft, Tag } from 'lucide-react';
import { TagManager } from '@/components/settings/tag-manager';

export default function TagsSettingsPage() {
  return (
    <div className="space-y-6">
      <div>
        <Link
          href="/settings"
          className="mb-2 inline-flex items-center gap-1 text-sm text-muted-foreground transition-colors hover:text-foreground"
        >
          <ChevronLeft className="h-4 w-4" />
          Settings
        </Link>
        <div className="flex items-center gap-2">
          <Tag className="h-6 w-6" />
          <h1 className="text-3xl font-bold tracking-tight">Tag Management</h1>
        </div>
        <p className="text-muted-foreground">
          Create, rename, recolor, and delete tags across your collection
        </p>
      </div>

      <TagManager />
    </div>
  );
}
