/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request body for adding a memory item to a context module.
 *
 * Attributes:
 * memory_id: ID of the memory item to associate.
 * ordering: Display/priority order within the module (default 0).
 */
export type AddMemoryToModuleRequest = {
  memory_id: string;
  ordering?: number;
};
