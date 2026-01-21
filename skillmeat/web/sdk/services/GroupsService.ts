/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AddGroupArtifactsRequest } from '../models/AddGroupArtifactsRequest';
import type { ArtifactPositionUpdate } from '../models/ArtifactPositionUpdate';
import type { CopyGroupRequest } from '../models/CopyGroupRequest';
import type { GroupArtifactResponse } from '../models/GroupArtifactResponse';
import type { GroupCreateRequest } from '../models/GroupCreateRequest';
import type { GroupListResponse } from '../models/GroupListResponse';
import type { GroupReorderRequest } from '../models/GroupReorderRequest';
import type { GroupResponse } from '../models/GroupResponse';
import type { GroupUpdateRequest } from '../models/GroupUpdateRequest';
import type { GroupWithArtifactsResponse } from '../models/GroupWithArtifactsResponse';
import type { ReorderArtifactsRequest } from '../models/ReorderArtifactsRequest';
import type { CancelablePromise } from '../core/CancelablePromise';
import type { BaseHttpRequest } from '../core/BaseHttpRequest';
export class GroupsService {
    constructor(public readonly httpRequest: BaseHttpRequest) {}
    /**
     * Create new group
     * Create a new group within a collection for organizing artifacts.
     *
     * Group names must be unique within their collection. Position determines
     * the display order (0-based, default 0).
     * @returns GroupResponse Successful Response
     * @throws ApiError
     */
    public createGroupApiV1GroupsPost({
        requestBody,
    }: {
        requestBody: GroupCreateRequest,
    }): CancelablePromise<GroupResponse> {
        return this.httpRequest.request({
            method: 'POST',
            url: '/api/v1/groups',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * List groups in collection
     * List all groups in a collection, ordered by position.
     *
     * Optionally filter by name using the search parameter, or filter to only
     * groups containing a specific artifact using the artifact_id parameter.
     * @returns GroupListResponse Successful Response
     * @throws ApiError
     */
    public listGroupsApiV1GroupsGet({
        collectionId,
        search,
        artifactId,
    }: {
        /**
         * Collection ID to list groups from
         */
        collectionId: string,
        /**
         * Filter groups by name (case-insensitive)
         */
        search?: (string | null),
        /**
         * Filter to groups containing this artifact
         */
        artifactId?: (string | null),
    }): CancelablePromise<GroupListResponse> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/v1/groups',
            query: {
                'collection_id': collectionId,
                'search': search,
                'artifact_id': artifactId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get group details
     * Get detailed information about a group including its artifacts.
     *
     * Artifacts are returned ordered by their position within the group.
     * @returns GroupWithArtifactsResponse Successful Response
     * @throws ApiError
     */
    public getGroupApiV1GroupsGroupIdGet({
        groupId,
    }: {
        groupId: string,
    }): CancelablePromise<GroupWithArtifactsResponse> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/v1/groups/{group_id}',
            path: {
                'group_id': groupId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Update group
     * Update group metadata (name, description, position).
     *
     * All fields are optional. Only provided fields will be updated.
     * @returns GroupResponse Successful Response
     * @throws ApiError
     */
    public updateGroupApiV1GroupsGroupIdPut({
        groupId,
        requestBody,
    }: {
        groupId: string,
        requestBody: GroupUpdateRequest,
    }): CancelablePromise<GroupResponse> {
        return this.httpRequest.request({
            method: 'PUT',
            url: '/api/v1/groups/{group_id}',
            path: {
                'group_id': groupId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete group
     * Delete a group from a collection.
     *
     * Artifacts are removed from the group but not deleted from the collection.
     * The group-artifact associations are cascaded automatically.
     * @returns void
     * @throws ApiError
     */
    public deleteGroupApiV1GroupsGroupIdDelete({
        groupId,
    }: {
        groupId: string,
    }): CancelablePromise<void> {
        return this.httpRequest.request({
            method: 'DELETE',
            url: '/api/v1/groups/{group_id}',
            path: {
                'group_id': groupId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Copy group to another collection
     * Copy a group with all its artifacts to another collection.
     *
     * The new group will have the same name with " (Copy)" suffix.
     * If an artifact is not already in the target collection, it will be added.
     * Duplicate artifacts (already in target collection) are silently skipped.
     * @returns GroupResponse Successful Response
     * @throws ApiError
     */
    public copyGroupApiV1GroupsGroupIdCopyPost({
        groupId,
        requestBody,
    }: {
        groupId: string,
        requestBody: CopyGroupRequest,
    }): CancelablePromise<GroupResponse> {
        return this.httpRequest.request({
            method: 'POST',
            url: '/api/v1/groups/{group_id}/copy',
            path: {
                'group_id': groupId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Bulk reorder groups
     * Update positions of multiple groups in a single transaction.
     *
     * This is more efficient than updating groups individually and ensures
     * atomic updates across all groups.
     * @returns GroupListResponse Successful Response
     * @throws ApiError
     */
    public reorderGroupsApiV1GroupsReorderPut({
        requestBody,
    }: {
        requestBody: GroupReorderRequest,
    }): CancelablePromise<GroupListResponse> {
        return this.httpRequest.request({
            method: 'PUT',
            url: '/api/v1/groups/reorder',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Add artifacts to group
     * Add one or more artifacts to a group.
     *
     * Artifacts can be added at a specific position (shifting existing artifacts)
     * or appended to the end (default). Duplicate artifacts are silently ignored.
     * @returns GroupWithArtifactsResponse Successful Response
     * @throws ApiError
     */
    public addArtifactsToGroupApiV1GroupsGroupIdArtifactsPost({
        groupId,
        requestBody,
    }: {
        groupId: string,
        requestBody: AddGroupArtifactsRequest,
    }): CancelablePromise<GroupWithArtifactsResponse> {
        return this.httpRequest.request({
            method: 'POST',
            url: '/api/v1/groups/{group_id}/artifacts',
            path: {
                'group_id': groupId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Remove artifact from group
     * Remove an artifact from a group.
     *
     * Remaining artifacts are automatically reordered to fill the gap.
     * The artifact itself is not deleted from the collection.
     * @returns void
     * @throws ApiError
     */
    public removeArtifactFromGroupApiV1GroupsGroupIdArtifactsArtifactIdDelete({
        groupId,
        artifactId,
    }: {
        groupId: string,
        artifactId: string,
    }): CancelablePromise<void> {
        return this.httpRequest.request({
            method: 'DELETE',
            url: '/api/v1/groups/{group_id}/artifacts/{artifact_id}',
            path: {
                'group_id': groupId,
                'artifact_id': artifactId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Update artifact position
     * Update an artifact's position within a group.
     *
     * Other artifacts are automatically shifted to accommodate the new position.
     * @returns GroupArtifactResponse Successful Response
     * @throws ApiError
     */
    public updateArtifactPositionApiV1GroupsGroupIdArtifactsArtifactIdPut({
        groupId,
        artifactId,
        requestBody,
    }: {
        groupId: string,
        artifactId: string,
        requestBody: ArtifactPositionUpdate,
    }): CancelablePromise<GroupArtifactResponse> {
        return this.httpRequest.request({
            method: 'PUT',
            url: '/api/v1/groups/{group_id}/artifacts/{artifact_id}',
            path: {
                'group_id': groupId,
                'artifact_id': artifactId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Bulk reorder artifacts
     * Update positions of multiple artifacts in a single transaction.
     *
     * This is more efficient than updating artifacts individually and ensures
     * atomic updates across all artifacts.
     * @returns GroupWithArtifactsResponse Successful Response
     * @throws ApiError
     */
    public reorderArtifactsInGroupApiV1GroupsGroupIdReorderArtifactsPost({
        groupId,
        requestBody,
    }: {
        groupId: string,
        requestBody: ReorderArtifactsRequest,
    }): CancelablePromise<GroupWithArtifactsResponse> {
        return this.httpRequest.request({
            method: 'POST',
            url: '/api/v1/groups/{group_id}/reorder-artifacts',
            path: {
                'group_id': groupId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
