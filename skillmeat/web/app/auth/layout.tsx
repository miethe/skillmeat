/**
 * Auth Layout
 *
 * Shared layout for auth pages (login, signup).
 * Bypasses the main app shell (Header + Navigation) to provide
 * a clean, centered presentation for Clerk auth forms.
 */

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-background px-4 py-12">
      <div className="mb-8 flex flex-col items-center gap-2">
        <span className="font-mono text-2xl font-bold tracking-tight text-foreground">
          SkillMeat
        </span>
        <p className="text-sm text-muted-foreground">Claude Code artifact collection manager</p>
      </div>
      {children}
    </div>
  );
}
