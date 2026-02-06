/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Validation error detail for a single field.
 *
 * Provides structured information about validation errors
 * that occur during request processing.
 */
export type ValidationErrorDetail = {
  /**
   * Name of the field that failed validation
   */
  field: string;
  /**
   * Error message describing the validation failure
   */
  message: string;
  /**
   * Type of validation error
   */
  type: string;
};
