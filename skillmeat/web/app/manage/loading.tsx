import { Loader2 } from 'lucide-react';

export default function Loading() {
  return (
    <div className="flex h-screen items-center justify-center">
      <div className="text-center">
        <Loader2 className="mx-auto mb-4 h-8 w-8 animate-spin text-primary" />
        <p className="text-sm text-muted-foreground">Loading entity management...</p>
      </div>
    </div>
  );
}
