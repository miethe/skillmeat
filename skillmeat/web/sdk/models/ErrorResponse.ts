/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ValidationErrorDetail } from './ValidationErrorDetail';
/**
 * Standard error response envelope.
 *
 * All API errors return this structure for consistent error handling
 * on the client side.
 */
export type ErrorResponse = {
    /**
     * Error type or code
     */
    error: string;
    /**
     * Human-readable error message
     */
    message: string;
    /**
     * Additional error details (optional)
     */
    details?: (Record<string, any> | null);
    /**
     * Validation errors for invalid requests
     */
    validation_errors?: (Array<ValidationErrorDetail> | null);
};

