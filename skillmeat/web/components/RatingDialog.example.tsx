/**
 * RatingDialog Component Examples
 *
 * Demonstrates usage patterns for the RatingDialog component.
 */

'use client';

import * as React from 'react';
import { RatingDialog } from './RatingDialog';
import { Button } from './ui/button';

/**
 * Example 1: Basic Rating Dialog
 */
export function BasicRatingDialogExample() {
  const [isOpen, setIsOpen] = React.useState(false);

  const handleSubmit = async (rating: number, feedback?: string) => {
    console.log('Rating submitted:', { rating, feedback });
    // Simulate API call
    await new Promise((resolve) => setTimeout(resolve, 1000));
  };

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold">Basic Rating Dialog</h3>
      <p className="text-sm text-muted-foreground">
        Simple rating dialog without initial rating
      </p>
      <Button onClick={() => setIsOpen(true)}>Rate Artifact</Button>
      <RatingDialog
        artifactId="skill-canvas-design"
        artifactName="Canvas Design"
        isOpen={isOpen}
        onClose={() => setIsOpen(false)}
        onSubmit={handleSubmit}
      />
    </div>
  );
}

/**
 * Example 2: Rating Dialog with Initial Rating
 */
export function PrefilledRatingDialogExample() {
  const [isOpen, setIsOpen] = React.useState(false);
  const [currentRating, setCurrentRating] = React.useState(4);

  const handleSubmit = async (rating: number, feedback?: string) => {
    console.log('Rating updated:', { rating, feedback });
    setCurrentRating(rating);
    await new Promise((resolve) => setTimeout(resolve, 1000));
  };

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold">Edit Existing Rating</h3>
      <p className="text-sm text-muted-foreground">
        Dialog opens with existing rating of {currentRating} stars
      </p>
      <Button onClick={() => setIsOpen(true)}>Edit Rating</Button>
      <RatingDialog
        artifactId="skill-document-skills"
        artifactName="Document Skills"
        isOpen={isOpen}
        onClose={() => setIsOpen(false)}
        onSubmit={handleSubmit}
        initialRating={currentRating}
      />
    </div>
  );
}

/**
 * Example 3: Rating Dialog with Error Handling
 */
export function ErrorHandlingRatingDialogExample() {
  const [isOpen, setIsOpen] = React.useState(false);

  const handleSubmit = async (rating: number, feedback?: string) => {
    console.log('Attempting to submit:', { rating, feedback });
    // Simulate API error
    await new Promise((resolve) => setTimeout(resolve, 500));
    throw new Error('Network error: Unable to submit rating. Please try again.');
  };

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold">Error Handling</h3>
      <p className="text-sm text-muted-foreground">
        Demonstrates error message display when submission fails
      </p>
      <Button onClick={() => setIsOpen(true)}>Rate (Will Fail)</Button>
      <RatingDialog
        artifactId="skill-api-explorer"
        artifactName="API Explorer"
        isOpen={isOpen}
        onClose={() => setIsOpen(false)}
        onSubmit={handleSubmit}
      />
    </div>
  );
}

/**
 * Example 4: Multiple Artifacts Rating List
 */
export function MultipleArtifactsExample() {
  const [openArtifact, setOpenArtifact] = React.useState<string | null>(null);

  const artifacts = [
    { id: 'skill-1', name: 'Canvas Design', rating: null },
    { id: 'skill-2', name: 'Document Skills', rating: 4 },
    { id: 'skill-3', name: 'API Explorer', rating: 5 },
  ];

  const handleSubmit = async (artifactId: string, rating: number, feedback?: string) => {
    console.log('Rating submitted for', artifactId, ':', { rating, feedback });
    await new Promise((resolve) => setTimeout(resolve, 1000));
    setOpenArtifact(null);
  };

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold">Multiple Artifacts</h3>
      <p className="text-sm text-muted-foreground">
        Rate multiple artifacts from a list
      </p>
      <div className="space-y-2">
        {artifacts.map((artifact) => (
          <div key={artifact.id} className="flex items-center justify-between p-3 border rounded-lg">
            <div>
              <p className="font-medium">{artifact.name}</p>
              {artifact.rating && (
                <p className="text-sm text-muted-foreground">
                  Current rating: {artifact.rating} stars
                </p>
              )}
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setOpenArtifact(artifact.id)}
            >
              {artifact.rating ? 'Edit Rating' : 'Rate'}
            </Button>
            {openArtifact === artifact.id && (
              <RatingDialog
                artifactId={artifact.id}
                artifactName={artifact.name}
                isOpen={true}
                onClose={() => setOpenArtifact(null)}
                onSubmit={(rating, feedback) => handleSubmit(artifact.id, rating, feedback)}
                initialRating={artifact.rating ?? undefined}
              />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

/**
 * Example 5: All Examples Showcase
 */
export default function RatingDialogExamples() {
  return (
    <div className="container mx-auto py-8 space-y-8 max-w-3xl">
      <div>
        <h1 className="text-3xl font-bold mb-2">RatingDialog Examples</h1>
        <p className="text-muted-foreground">
          Explore different use cases for the RatingDialog component
        </p>
      </div>

      <div className="space-y-8">
        <BasicRatingDialogExample />
        <hr />
        <PrefilledRatingDialogExample />
        <hr />
        <ErrorHandlingRatingDialogExample />
        <hr />
        <MultipleArtifactsExample />
      </div>

      <div className="mt-8 p-4 bg-muted rounded-lg">
        <h3 className="font-semibold mb-2">Features Demonstrated</h3>
        <ul className="list-disc list-inside space-y-1 text-sm">
          <li>Star-based rating (1-5 stars)</li>
          <li>Optional feedback textarea</li>
          <li>Keyboard navigation (Arrow keys, Tab, Enter, Escape)</li>
          <li>Loading states during submission</li>
          <li>Error handling and display</li>
          <li>Initial rating for editing existing ratings</li>
          <li>Full ARIA accessibility support</li>
          <li>Responsive mobile design</li>
        </ul>
      </div>
    </div>
  );
}
