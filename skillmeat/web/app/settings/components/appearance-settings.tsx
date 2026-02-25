'use client';

import * as React from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Palette, Shapes } from 'lucide-react';
import { ColorsSettings } from './colors-settings';
import { IconsSettings } from './icons-settings';

// ---------------------------------------------------------------------------
// AppearanceSettings
// ---------------------------------------------------------------------------

/**
 * Appearance settings panel with "Colors" and "Icons" sub-tabs.
 * Rendered inside the "Appearance" tab of the global Settings page.
 */
export function AppearanceSettings() {
  return (
    <Tabs defaultValue="colors">
      <TabsList className="mb-4">
        <TabsTrigger value="colors" className="flex items-center gap-2">
          <Palette className="h-4 w-4" />
          Colors
        </TabsTrigger>
        <TabsTrigger value="icons" className="flex items-center gap-2">
          <Shapes className="h-4 w-4" />
          Icons
        </TabsTrigger>
      </TabsList>

      {/* Colors sub-tab */}
      <TabsContent value="colors" className="space-y-4">
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Palette className="h-5 w-5" />
              <CardTitle>Color Settings</CardTitle>
            </div>
            <CardDescription>
              Manage preset colors and custom color palettes used across SkillMeat.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ColorsSettings />
          </CardContent>
        </Card>
      </TabsContent>

      {/* Icons sub-tab */}
      <TabsContent value="icons" className="space-y-4">
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Shapes className="h-5 w-5" />
              <CardTitle>Icon Settings</CardTitle>
            </div>
            <CardDescription>
              Configure icon packs and default icons used for groups and artifacts.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <IconsSettings />
          </CardContent>
        </Card>
      </TabsContent>
    </Tabs>
  );
}
