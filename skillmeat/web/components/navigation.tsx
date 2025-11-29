'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import {
  Database,
  FolderCog,
  GitBranch,
  Home,
  Package,
  Settings,
  ShoppingBag,
  Users,
} from 'lucide-react';

const navItems = [
  {
    title: 'Dashboard',
    href: '/',
    icon: Home,
  },
  {
    title: 'Manage',
    href: '/manage',
    icon: FolderCog,
  },
  {
    title: 'Collection',
    href: '/collection',
    icon: Package,
  },
  {
    title: 'Projects',
    href: '/projects',
    icon: GitBranch,
  },
  {
    title: 'Marketplace',
    href: '/marketplace',
    icon: ShoppingBag,
  },
  {
    title: 'Sharing',
    href: '/sharing',
    icon: Users,
  },
  {
    title: 'MCP Servers',
    href: '/mcp',
    icon: Database,
  },
  {
    title: 'Settings',
    href: '/settings',
    icon: Settings,
  },
];

export function Navigation() {
  const pathname = usePathname();

  return (
    <aside className="w-64 border-r bg-background">
      <nav className="space-y-1 p-4">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href || pathname.startsWith(`${item.href}/`);

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-secondary text-secondary-foreground'
                  : 'text-muted-foreground hover:bg-secondary/50 hover:text-foreground'
              )}
            >
              <Icon className="h-4 w-4" />
              {item.title}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
