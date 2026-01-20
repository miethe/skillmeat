/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Response model for file content from a marketplace artifact.
 *
 * Contains the file content along with metadata for rendering in the UI.
 * Binary files will have base64-encoded content with is_binary=True.
 * Large files (>1MB) are truncated to 10,000 lines with truncated=True.
 */
export type skillmeat__api__schemas__marketplace__FileContentResponse = {
    /**
     * File content (text or base64-encoded for binary files)
     */
    content: string;
    /**
     * Content encoding: 'none' for text, 'base64' for binary
     */
    encoding: string;
    /**
     * File size in bytes (may be truncated size if truncated=True)
     */
    size: number;
    /**
     * Git blob SHA
     */
    sha: string;
    /**
     * File name
     */
    name: string;
    /**
     * Full path within repository
     */
    path: string;
    /**
     * Whether the file is binary (content is base64)
     */
    is_binary: boolean;
    /**
     * Path to the artifact this file belongs to
     */
    artifact_path: string;
    /**
     * ID of the marketplace source
     */
    source_id: string;
    /**
     * Whether the content was truncated due to size (>1MB)
     */
    truncated?: boolean;
    /**
     * Original file size in bytes (only set when truncated=True)
     */
    original_size?: (number | null);
};

