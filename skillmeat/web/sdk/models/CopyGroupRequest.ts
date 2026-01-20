/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request schema for copying a group to another collection.
 *
 * Creates a copy of the group (with name + " (Copy)") in the target collection,
 * including all artifacts from the source group.
 */
export type CopyGroupRequest = {
  /**
   * ID of the collection to copy the group to
   */
  target_collection_id: string;
};
