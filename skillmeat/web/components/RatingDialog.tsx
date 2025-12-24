/**
 * RatingDialog Component
 *
 * Accessible star-picker dialog for collecting artifact ratings and feedback.
 *
 * Features:
 * - 1-5 star rating with hover preview
 * - Optional feedback textarea
 * - Full keyboard accessibility (Tab, Arrow keys, Enter, Escape)
 * - ARIA labels for screen readers
 * - Loading and error states
 * - Responsive mobile design
 *
 * @example
 * ```tsx
 * const [isOpen, setIsOpen] = useState(false);
 *
 * const handleSubmit = async (rating: number, feedback?: string) => {
 *   await submitRating(artifactId, rating, feedback);
 * };
 *
 * <RatingDialog
 *   artifactId="skill-123"
 *   artifactName="Canvas Design"
 *   isOpen={isOpen}
 *   onClose={() => setIsOpen(false)}
 *   onSubmit={handleSubmit}
 *   initialRating={4}
 * />
 * ```
 */

'use client';

import * as React from 'react';
import { Star } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { cn } from '@/lib/utils';

export interface RatingDialogProps {
  /** Artifact identifier */
  artifactId: string;
  /** Artifact name for display */
  artifactName: string;
  /** Dialog open state */
  isOpen: boolean;
  /** Close dialog callback */
  onClose: () => void;
  /** Submit rating callback (returns Promise) */
  onSubmit: (rating: number, feedback?: string) => Promise<void>;
  /** Initial rating value (1-5) */
  initialRating?: number;
}

/**
 * RatingDialog - Star-picker dialog for artifact ratings
 *
 * Displays a modal dialog with 5-star rating picker and optional feedback.
 * Fully keyboard accessible with ARIA support for screen readers.
 */
export function RatingDialog({
  artifactId, // eslint-disable-line @typescript-eslint/no-unused-vars -- Reserved for future analytics tracking
  artifactName,
  isOpen,
  onClose,
  onSubmit,
  initialRating,
}: RatingDialogProps) {
  const [rating, setRating] = React.useState<number | null>(initialRating ?? null);
  const [hoveredRating, setHoveredRating] = React.useState<number | null>(null);
  const [feedback, setFeedback] = React.useState('');
  const [isLoading, setIsLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const starContainerRef = React.useRef<HTMLDivElement>(null);

  // Reset state when dialog opens
  React.useEffect(() => {
    if (isOpen) {
      setRating(initialRating ?? null);
      setFeedback('');
      setError(null);
      setIsLoading(false);
    }
  }, [isOpen, initialRating]);

  const handleStarClick = (starRating: number) => {
    setRating(starRating);
    setError(null);
  };

  const handleStarHover = (starRating: number) => {
    setHoveredRating(starRating);
  };

  const handleStarLeave = () => {
    setHoveredRating(null);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowRight') {
      e.preventDefault();
      setRating((prev) => Math.min((prev ?? 0) + 1, 5));
      setError(null);
    } else if (e.key === 'ArrowLeft') {
      e.preventDefault();
      setRating((prev) => Math.max((prev ?? 1) - 1, 1));
      setError(null);
    } else if (e.key === 'Enter' && rating !== null && !isLoading) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleSubmit = async () => {
    if (rating === null) {
      setError('Please select a rating');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      await onSubmit(rating, feedback || undefined);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit rating');
      setIsLoading(false);
    }
  };

  const handleCancel = () => {
    onClose();
  };

  const displayRating = hoveredRating ?? rating ?? 0;

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && handleCancel()}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Rate {artifactName}</DialogTitle>
          <DialogDescription>Share your experience with this artifact</DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Star Picker */}
          <div
            ref={starContainerRef}
            className="flex flex-col items-center gap-3"
            onKeyDown={handleKeyDown}
            role="group"
            aria-label={`Rating: ${rating ?? 0} out of 5 stars`}
            tabIndex={0}
          >
            <div className="flex gap-2">
              {[1, 2, 3, 4, 5].map((starNumber) => (
                <button
                  key={starNumber}
                  type="button"
                  onClick={() => handleStarClick(starNumber)}
                  onMouseEnter={() => handleStarHover(starNumber)}
                  onMouseLeave={handleStarLeave}
                  aria-label={`Rate ${starNumber} star${starNumber > 1 ? 's' : ''}`}
                  className={cn(
                    'transition-transform hover:scale-110 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 rounded',
                    'p-1'
                  )}
                  disabled={isLoading}
                >
                  <Star
                    className={cn(
                      'w-8 h-8 sm:w-10 sm:h-10 transition-colors',
                      starNumber <= displayRating
                        ? 'fill-yellow-500 text-yellow-500'
                        : 'fill-gray-200 text-gray-400'
                    )}
                  />
                </button>
              ))}
            </div>
            {rating !== null && (
              <p className="text-sm text-muted-foreground" aria-live="polite">
                {rating} star{rating > 1 ? 's' : ''}
              </p>
            )}
          </div>

          {/* Feedback Textarea */}
          <div className="space-y-2">
            <label htmlFor="feedback" className="text-sm font-medium">
              Feedback (optional)
            </label>
            <Textarea
              id="feedback"
              placeholder="Tell us about your experience..."
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              disabled={isLoading}
              aria-label="Optional feedback"
              className="min-h-[100px] resize-none"
              maxLength={1000}
            />
            <p className="text-xs text-muted-foreground text-right">
              {feedback.length}/1000 characters
            </p>
          </div>

          {/* Error Message */}
          {error && (
            <div
              className="rounded-md bg-destructive/10 p-3 text-sm text-destructive"
              role="alert"
              aria-live="assertive"
            >
              {error}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleCancel} disabled={isLoading}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={rating === null || isLoading}>
            {isLoading ? (
              <>
                <span className="mr-2">Submitting...</span>
                <span
                  className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-solid border-current border-r-transparent"
                  aria-label="Loading"
                />
              </>
            ) : (
              'Submit'
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
