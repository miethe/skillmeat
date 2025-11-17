import type { Metadata } from 'next';
import './globals.css';
import { Header } from '@/components/header';
import { Navigation } from '@/components/navigation';
import { Providers } from '@/components/providers';

export const metadata: Metadata = {
  title: {
    default: 'SkillMeat - Collection Manager',
    template: '%s | SkillMeat',
  },
  description:
    'Personal collection manager for Claude Code artifacts (Skills, Commands, Agents, MCP, Hooks)',
  keywords: ['claude', 'skills', 'commands', 'agents', 'mcp', 'collection manager', 'artifacts'],
  authors: [{ name: 'SkillMeat Contributors' }],
  openGraph: {
    type: 'website',
    locale: 'en_US',
    url: 'https://github.com/miethe/skillmeat',
    title: 'SkillMeat - Collection Manager',
    description:
      'Personal collection manager for Claude Code artifacts (Skills, Commands, Agents, MCP, Hooks)',
    siteName: 'SkillMeat',
  },
  robots: {
    index: true,
    follow: true,
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="font-sans antialiased">
        <Providers>
          <div className="flex min-h-screen flex-col">
            <Header />
            <div className="flex flex-1">
              <Navigation />
              <main className="flex-1 p-6">{children}</main>
            </div>
          </div>
        </Providers>
      </body>
    </html>
  );
}
