"use client";

/**
 * Team Sharing Page
 *
 * Export, import, and manage artifact bundles with team members
 */

import { useState } from "react";
import { Package, Upload, Download, Share2, Users } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ExportDialog } from "@/components/sharing/export-dialog";
import { ImportDialog } from "@/components/sharing/import-dialog";
import { BundleList } from "@/components/sharing/bundle-list";
import { PermissionBadge } from "@/components/sharing/permission-badge";

export default function SharingPage() {
  const [showExportDialog, setShowExportDialog] = useState(false);
  const [showImportDialog, setShowImportDialog] = useState(false);
  const [activeTab, setActiveTab] = useState<"created" | "imported">("created");

  // Mock user permission - would come from auth context in real app
  const userPermission: "viewer" | "importer" | "publisher" | "admin" = "publisher";
  const canExport = ["publisher", "admin"].includes(userPermission);
  const canImport = ["importer", "publisher", "admin"].includes(userPermission);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Team Sharing</h1>
          <p className="text-muted-foreground mt-1">
            Share and collaborate on artifact bundles
          </p>
        </div>
        <div className="flex items-center gap-2">
          <PermissionBadge level={userPermission} />
        </div>
      </div>

      {/* Quick Actions */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card className="hover:shadow-md transition-shadow">
          <CardHeader>
            <div className="flex items-center gap-2">
              <div className="p-2 rounded-lg bg-primary/10">
                <Package className="h-5 w-5 text-primary" />
              </div>
              <div className="flex-1">
                <CardTitle className="text-base">Export Bundles</CardTitle>
                <CardDescription className="text-xs">
                  Create shareable bundles from your collection
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground mb-4">
              Package selected artifacts into .skillmeat-pack bundles for sharing with team
              members. Generate shareable links with customizable permissions and expiration.
            </p>
            <Button
              onClick={() => setShowExportDialog(true)}
              disabled={!canExport}
              className="w-full"
            >
              <Upload className="h-4 w-4 mr-2" />
              Create Bundle
            </Button>
            {!canExport && (
              <p className="text-xs text-muted-foreground text-center mt-2">
                Publisher or Admin role required
              </p>
            )}
          </CardContent>
        </Card>

        <Card className="hover:shadow-md transition-shadow">
          <CardHeader>
            <div className="flex items-center gap-2">
              <div className="p-2 rounded-lg bg-primary/10">
                <Download className="h-5 w-5 text-primary" />
              </div>
              <div className="flex-1">
                <CardTitle className="text-base">Import Bundles</CardTitle>
                <CardDescription className="text-xs">
                  Import shared bundles into your collection
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground mb-4">
              Import bundles from files, URLs, or cloud vaults. Preview contents and choose
              conflict resolution strategy before importing.
            </p>
            <Button
              onClick={() => setShowImportDialog(true)}
              disabled={!canImport}
              variant="outline"
              className="w-full"
            >
              <Download className="h-4 w-4 mr-2" />
              Import Bundle
            </Button>
            {!canImport && (
              <p className="text-xs text-muted-foreground text-center mt-2">
                Importer or higher role required
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Bundle Management */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Share2 className="h-5 w-5" />
              <CardTitle>Your Bundles</CardTitle>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as any)}>
            <TabsList className="grid w-full grid-cols-2 mb-6">
              <TabsTrigger value="created">
                <Package className="h-4 w-4 mr-2" />
                Created
              </TabsTrigger>
              <TabsTrigger value="imported">
                <Download className="h-4 w-4 mr-2" />
                Imported
              </TabsTrigger>
            </TabsList>

            <TabsContent value="created" className="mt-0">
              <BundleList filter="created" />
            </TabsContent>

            <TabsContent value="imported" className="mt-0">
              <BundleList filter="imported" />
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      {/* Info Section */}
      <Card className="border-primary/20 bg-primary/5">
        <CardHeader>
          <div className="flex items-center gap-2">
            <Users className="h-5 w-5 text-primary" />
            <CardTitle className="text-base">Collaboration Tips</CardTitle>
          </div>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-muted-foreground">
          <ul className="list-disc list-inside space-y-1">
            <li>
              Use descriptive names and tags to make bundles easy to find
            </li>
            <li>
              Include dependencies to ensure artifacts work correctly when imported
            </li>
            <li>
              Set appropriate permission levels for sensitive bundles
            </li>
            <li>
              Use expiring links for temporary sharing or trial access
            </li>
            <li>
              Monitor analytics to see which artifacts are most popular
            </li>
          </ul>
        </CardContent>
      </Card>

      {/* Dialogs */}
      <ExportDialog
        isOpen={showExportDialog}
        onClose={() => setShowExportDialog(false)}
      />

      <ImportDialog
        isOpen={showImportDialog}
        onClose={() => setShowImportDialog(false)}
        onSuccess={() => {
          // Refresh the imported bundles list
          setActiveTab("imported");
        }}
      />
    </div>
  );
}
