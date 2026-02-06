/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Single validation issue.
 */
export type ValidationIssueResponse = {
  /**
   * Issue severity (error, warning, info)
   */
  severity: string;
  /**
   * Issue category (security, schema, integrity, size)
   */
  category: string;
  /**
   * Issue message
   */
  message: string;
  /**
   * File path if issue relates to specific file
   */
  file_path?: string | null;
};
