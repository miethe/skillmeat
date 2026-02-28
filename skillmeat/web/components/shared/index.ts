/**
 * Shared components barrel export
 *
 * Components in this directory are used across two or more features.
 * Import from this barrel rather than individual files:
 *
 *   import { ColorSelector } from '@/components/shared';
 */

export { ArtifactPicker, type ArtifactPickerProps } from './artifact-picker';
export { ColorSelector, type ColorSelectorProps } from './color-selector';
export { ContextModulePicker, type ContextModulePickerProps } from './context-module-picker';
export { IconPicker, type IconPickerProps } from './icon-picker';
export { InlineEdit, type InlineEditProps } from './inline-edit';
export { SlideOverPanel, type SlideOverPanelProps, type SlideOverPanelWidth } from './slide-over-panel';
