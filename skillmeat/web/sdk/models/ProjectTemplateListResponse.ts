/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { PageInfo } from './PageInfo';
import type { ProjectTemplateResponse } from './ProjectTemplateResponse';
/**
 * Paginated response for project template listings.
 *
 * Inherits pagination metadata from PaginatedResponse:
 * - items: List of project templates
 * - page_info: Cursor-based pagination information
 *
 * Example:
 * >>> response = ProjectTemplateListResponse(
     * ...     items=[template1, template2],
     * ...     page_info=PageInfo(
         * ...         has_next_page=True,
         * ...         has_previous_page=False,
         * ...         end_cursor="cursor123"
         * ...     )
         * ... )
         */
        export type ProjectTemplateListResponse = {
            /**
             * List of items for this page
             */
            items: Array<ProjectTemplateResponse>;
            /**
             * Pagination metadata
             */
            page_info: PageInfo;
        };

