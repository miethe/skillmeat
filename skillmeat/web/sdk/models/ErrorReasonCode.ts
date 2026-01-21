/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Reason codes for import failures and skips.
 *
 * These codes provide machine-readable reasons for why an artifact
 * was skipped or failed during bulk import, enabling frontend
 * error handling and reporting.
 */
export type ErrorReasonCode = 'invalid_structure' | 'yaml_parse_error' | 'missing_metadata' | 'invalid_type' | 'invalid_source' | 'import_error' | 'network_error' | 'permission_error' | 'io_error' | 'already_exists' | 'in_skip_list' | 'duplicate';
