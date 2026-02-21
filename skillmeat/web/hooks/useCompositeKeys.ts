/**
 * Re-export compositeKeys from the canonical source.
 *
 * The query key factory lives in useImportComposite.ts which was already
 * part of the codebase.  This file exists for convenience only.
 *
 * @deprecated Import directly from './useImportComposite' if you need compositeKeys.
 */
export { compositeKeys } from './useImportComposite';
