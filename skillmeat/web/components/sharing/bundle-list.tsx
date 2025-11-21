"use client";

/**
 * Bundle List Component
 *
 * Display list of created and imported bundles with analytics
 */

import { useState } from "react";
import {
  Package,
  Download,
  Trash2,
  Share2,
  Calendar,
  FileArchive,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ShareLink } from "./share-link";
import { useBundles, useDeleteBundle, useBundleAnalytics } from "@/hooks/useBundles";
import type { BundleListItem } from "@/types/bundle";

export interface BundleListProps {
  filter?: "created" | "imported" | "all";
}

export function BundleList({ filter = "all" }: BundleListProps) {
  const { data: bundles, isLoading } = useBundles(filter);
  const [selectedBundle, setSelectedBundle] = useState<BundleListItem | null>(null);
  const [showShareDialog, setShowShareDialog] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);

  const deleteMutation = useDeleteBundle();
  const { data: analytics } = useBundleAnalytics(selectedBundle?.id || null);

  const handleDelete = async () => {
    if (!selectedBundle) return;

    try {
      await deleteMutation.mutateAsync(selectedBundle.id);
      setShowDeleteDialog(false);
      setSelectedBundle(null);
    } catch (error) {
      console.error("Failed to delete bundle:", error);
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <Card key={i} className="animate-pulse">
            <CardContent className="p-6">
              <div className="h-4 bg-muted rounded w-1/3 mb-2" />
              <div className="h-3 bg-muted rounded w-2/3" />
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  if (!bundles || bundles.length === 0) {
    return (
      <Card>
        <CardContent className="p-12 text-center">
          <Package className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
          <h3 className="text-lg font-semibold mb-2">No bundles yet</h3>
          <p className="text-sm text-muted-foreground">
            {filter === "created"
              ? "Create your first bundle to share artifacts with others"
              : filter === "imported"
              ? "Import bundles shared by others to get started"
              : "No bundles available"}
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <>
      <div className="space-y-3">
        {bundles.map((bundle) => (
          <Card
            key={bundle.id}
            className="hover:shadow-md transition-shadow cursor-pointer group"
          >
            <CardContent className="p-6">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-start gap-3">
                    <div className="p-2 rounded-lg bg-primary/10 flex-shrink-0">
                      <Package className="h-5 w-5 text-primary" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="font-semibold text-base truncate">
                          {bundle.metadata?.name || "Unnamed Bundle"}
                        </h3>
                        {bundle.isImported && (
                          <Badge variant="secondary" className="text-xs flex-shrink-0">
                            Imported
                          </Badge>
                        )}
                      </div>

                      {bundle.metadata.description && (
                        <p className="text-sm text-muted-foreground line-clamp-2 mb-3">
                          {bundle.metadata.description}
                        </p>
                      )}

                      {bundle.metadata.tags && bundle.metadata.tags.length > 0 && (
                        <div className="flex flex-wrap gap-1 mb-3">
                          {bundle.metadata.tags.slice(0, 3).map((tag) => (
                            <Badge key={tag} variant="outline" className="text-xs">
                              {tag}
                            </Badge>
                          ))}
                          {bundle.metadata.tags.length > 3 && (
                            <Badge variant="outline" className="text-xs">
                              +{bundle.metadata.tags.length - 3}
                            </Badge>
                          )}
                        </div>
                      )}

                      <div className="flex flex-wrap items-center gap-4 text-xs text-muted-foreground">
                        <div className="flex items-center gap-1">
                          <FileArchive className="h-3 w-3" />
                          <span>{bundle.artifactCount} artifacts</span>
                        </div>
                        <div className="flex items-center gap-1">
                          <Download className="h-3 w-3" />
                          <span>{(bundle.size / 1024 / 1024).toFixed(2)} MB</span>
                        </div>
                        <div className="flex items-center gap-1">
                          <Calendar className="h-3 w-3" />
                          <span>
                            {new Date(bundle.exportedAt).toLocaleDateString()}
                          </span>
                        </div>
                        {bundle.shareLink && (
                          <div className="flex items-center gap-1">
                            <Share2 className="h-3 w-3" />
                            <span>{bundle.downloadCount} downloads</span>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2 flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
                  {bundle.shareLink && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedBundle(bundle);
                        setShowShareDialog(true);
                      }}
                    >
                      <Share2 className="h-4 w-4 mr-1" />
                      Share
                    </Button>
                  )}
                  {!bundle.isImported && (
                    <Button
                      variant="outline"
                      size="icon"
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedBundle(bundle);
                        setShowDeleteDialog(true);
                      }}
                    >
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Share Dialog */}
      {selectedBundle?.shareLink && (
        <Dialog open={showShareDialog} onOpenChange={setShowShareDialog}>
          <DialogContent className="sm:max-w-[500px]">
            <DialogHeader>
              <DialogTitle>Share Bundle</DialogTitle>
              <DialogDescription>
                Share {selectedBundle.metadata?.name || "this bundle"} with others
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <ShareLink
                shareLink={selectedBundle.shareLink}
                showAnalytics={true}
              />

              {analytics && (
                <div className="rounded-lg border p-4 space-y-3">
                  <h4 className="text-sm font-medium">Analytics</h4>
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <p className="text-muted-foreground">Total Downloads</p>
                      <p className="font-medium text-lg">{analytics.downloads}</p>
                    </div>
                    <div>
                      <p className="text-muted-foreground">Unique Users</p>
                      <p className="font-medium text-lg">
                        {analytics.uniqueDownloaders}
                      </p>
                    </div>
                  </div>
                  {analytics.lastDownloaded && (
                    <div className="pt-2 border-t text-xs text-muted-foreground">
                      Last downloaded:{" "}
                      {new Date(analytics.lastDownloaded).toLocaleString()}
                    </div>
                  )}

                  {analytics.popularArtifacts.length > 0 && (
                    <div className="pt-2 border-t">
                      <p className="text-xs font-medium mb-2">Popular Artifacts</p>
                      <div className="space-y-1">
                        {analytics.popularArtifacts.map((artifact) => (
                          <div
                            key={artifact.artifactId}
                            className="flex items-center justify-between text-xs"
                          >
                            <span className="text-muted-foreground">
                              {artifact.artifactName}
                            </span>
                            <span className="font-medium">
                              {artifact.downloads} downloads
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
            <DialogFooter>
              <Button onClick={() => setShowShareDialog(false)}>Close</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}

      {/* Delete Confirmation Dialog */}
      <Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <DialogContent className="sm:max-w-[400px]">
          <DialogHeader>
            <DialogTitle>Delete Bundle?</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete "{selectedBundle?.metadata?.name || "this bundle"}"? This
              action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setShowDeleteDialog(false)}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={deleteMutation.isPending}
            >
              {deleteMutation.isPending ? "Deleting..." : "Delete"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
