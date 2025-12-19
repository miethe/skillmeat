/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Response schema for sync conflict information.
 *
 * Attributes:
 * entity_id: Entity identifier
 * entity_name: Entity name
 * entity_type: Entity type (spec_file, rule_file, etc.)
 * collection_hash: Hash in collection
 * deployed_hash: Hash of deployed file
 * collection_content: Current content in collection
 * deployed_content: Current content in deployed file
 * collection_path: Path to entity in collection
 * deployed_path: Path to deployed file in project
 * change_origin: Origin of the change (optional)
 * baseline_hash: Hash at deployment time (baseline for three-way merge)
 */
export type SyncConflictResponse = {
    /**
     * Entity identifier
     */
    entity_id: string;
    /**
     * Entity name
     */
    entity_name: string;
    /**
     * Entity type
     */
    entity_type: string;
    /**
     * Content hash in collection
     */
    collection_hash: string;
    /**
     * Content hash of deployed file
     */
    deployed_hash: string;
    /**
     * Current content in collection
     */
    collection_content: string;
    /**
     * Current content in deployed file
     */
    deployed_content: string;
    /**
     * Path to entity in collection
     */
    collection_path: string;
    /**
     * Path to deployed file in project
     */
    deployed_path: string;
    /**
     * Origin of the change (deployment/sync/local_modification)
     */
    change_origin?: (string | null);
    /**
     * Hash at deployment time (baseline for three-way merge)
     */
    baseline_hash?: (string | null);
};

