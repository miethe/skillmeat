import Link from 'next/link';
import Image from 'next/image';

export function Header() {
  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container flex h-14 items-center">
        <div className="mr-4 flex">
          <Link href="/" className="mr-6 flex items-center space-x-2">
            <Image src="/logo.png" alt="SkillMeat Logo" width={32} height={32} className="h-8 w-auto" />
            <span className="font-bold">SkillMeat</span>
          </Link>
        </div>
        <div className="flex flex-1 items-center justify-between space-x-2 md:justify-end">
          <nav className="flex items-center space-x-6 text-sm font-medium">
            <Link
              href="https://github.com/miethe/skillmeat"
              target="_blank"
              rel="noreferrer"
              className="text-foreground/60 transition-colors hover:text-foreground/80"
            >
              GitHub
            </Link>
            <Link
              href="https://github.com/miethe/skillmeat#readme"
              target="_blank"
              rel="noreferrer"
              className="text-foreground/60 transition-colors hover:text-foreground/80"
            >
              Documentation
            </Link>
          </nav>
        </div>
      </div>
    </header>
  );
}
