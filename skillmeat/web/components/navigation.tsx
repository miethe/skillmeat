'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import {
  LayoutDashboard,
  FolderOpen,
  Grid3x3,
  Layers,
  Settings2,
  FolderKanban,
  Server,
  Store,
  GitBranch,
  Share2,
  Settings,
  FileText,
  FileCode2,
  Github,
  Book,
} from 'lucide-react';
import { NavSection } from './nav-section';
import { CollectionSwitcherWithDialogs } from './collection/collection-switcher-with-dialogs';
import type { LucideIcon } from 'lucide-react';

// ============================================================================
// Types
// ============================================================================

interface NavItem {
  name: string;
  href: string;
  icon: LucideIcon;
}

interface NavSectionConfig {
  title: string;
  icon: LucideIcon;
  storageKey: string;
  defaultExpanded?: boolean;
  items: NavItem[];
}

interface NavigationConfig {
  topItems: NavItem[];
  sections: NavSectionConfig[];
  bottomItems: NavItem[];
}

// ============================================================================
// Navigation Configuration
// ============================================================================

const navigationConfig: NavigationConfig = {
  topItems: [{ name: 'Dashboard', href: '/', icon: LayoutDashboard }],
  sections: [
    {
      title: 'Collections',
      icon: FolderOpen,
      storageKey: 'collections',
      defaultExpanded: true,
      items: [
        { name: 'Browse', href: '/collection', icon: Grid3x3 },
        { name: 'Groups', href: '/groups', icon: Layers },
        { name: 'Manage', href: '/manage', icon: Settings2 },
        { name: 'Projects', href: '/projects', icon: FolderKanban },
        { name: 'MCP Servers', href: '/mcp', icon: Server },
      ],
    },
    {
      title: 'Marketplace',
      icon: Store,
      storageKey: 'marketplace',
      items: [{ name: 'Sources', href: '/marketplace/sources', icon: GitBranch }],
    },
    {
      title: 'Agent Context',
      icon: FileText,
      storageKey: 'agent-context',
      items: [
        { name: 'Context Entities', href: '/context-entities', icon: FileCode2 },
        { name: 'Templates', href: '/templates', icon: FileText },
      ],
    },
    {
      title: 'Resources',
      icon: Book,
      storageKey: 'resources',
      items: [
        { name: 'GitHub', href: 'https://github.com/miethe/skillmeat', icon: Github },
        { name: 'Documentation', href: 'https://github.com/miethe/skillmeat#readme', icon: Book },
      ],
    },
  ],
  bottomItems: [
    { name: 'Sharing', href: '/sharing', icon: Share2 },
    { name: 'Settings', href: '/settings', icon: Settings },
  ],
};

// ============================================================================
// Main Component
// ============================================================================

/**
 * Navigation - Sidebar navigation component
 *
 * Provides hierarchical navigation with collapsible sections.
 * Supports:
 * - Top-level items (always visible)
 * - Collapsible sections with nested items
 * - Bottom-level items (always visible)
 * - Active state highlighting
 * - Keyboard navigation
 * - localStorage persistence
 */
export function Navigation() {
  const pathname = usePathname();

  return (
    <aside className="w-64 border-r bg-background">
      <nav className="space-y-1 p-4">
        {/* Collection Switcher */}
        <div className="mb-4">
          <CollectionSwitcherWithDialogs className="w-full" />
        </div>

        {/* Top Items */}
        {navigationConfig.topItems.map((item) => {
          const Icon = item.icon;
          const isActive =
            pathname === item.href || (item.href !== '/' && pathname.startsWith(`${item.href}/`));

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:bg-secondary/50 hover:text-foreground',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2'
              )}
            >
              <Icon className="h-4 w-4" />
              {item.name}
            </Link>
          );
        })}

        {/* Collapsible Sections */}
        {navigationConfig.sections.map((section) => (
          <NavSection
            key={section.storageKey}
            title={section.title}
            icon={section.icon}
            items={section.items}
            defaultExpanded={section.defaultExpanded}
            storageKey={section.storageKey}
          />
        ))}

        {/* Bottom Items */}
        {navigationConfig.bottomItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href || pathname.startsWith(`${item.href}/`);

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:bg-secondary/50 hover:text-foreground',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2'
              )}
            >
              <Icon className="h-4 w-4" />
              {item.name}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
