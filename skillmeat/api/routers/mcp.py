"""MCP server management API endpoints.

Provides REST API for managing MCP servers within collections and deploying
them to Claude Desktop.
"""

import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from skillmeat.api.dependencies import (
    CollectionManagerDep,
    ConfigManagerDep,
    verify_api_key,
)
from skillmeat.api.middleware.auth import TokenDep
from skillmeat.api.schemas.common import ErrorResponse
from skillmeat.api.schemas.mcp import (
    DeploymentRequest,
    DeploymentResponse,
    DeploymentStatusResponse,
    MCPServerCreateRequest,
    MCPServerListResponse,
    MCPServerResponse,
    MCPServerUpdateRequest,
)
from skillmeat.core.mcp.deployment import MCPDeploymentManager
from skillmeat.core.mcp.metadata import MCPServerMetadata, MCPServerStatus

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/mcp",
    tags=["mcp"],
    dependencies=[Depends(verify_api_key)],  # All endpoints require API key
)


def metadata_to_response(server: MCPServerMetadata) -> MCPServerResponse:
    """Convert MCPServerMetadata to API response schema.

    Args:
        server: MCP server metadata

    Returns:
        MCPServerResponse schema
    """
    return MCPServerResponse(
        name=server.name,
        repo=server.repo,
        version=server.version,
        description=server.description,
        env_vars=server.env_vars,
        status=server.status.value,
        installed_at=server.installed_at,
        resolved_sha=server.resolved_sha,
        resolved_version=server.resolved_version,
        last_updated=server.last_updated,
    )


@router.get(
    "/servers",
    response_model=MCPServerListResponse,
    summary="List all MCP servers",
    description="Retrieve all MCP servers in the collection",
    responses={
        200: {"description": "Successfully retrieved MCP servers"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def list_mcp_servers(
    collection_mgr: CollectionManagerDep,
    token: TokenDep,
    collection: Optional[str] = Query(
        default=None,
        description="Collection name (uses default if not specified)",
    ),
) -> MCPServerListResponse:
    """List all MCP servers in collection.

    Args:
        collection_mgr: Collection manager dependency
        token: Authentication token
        collection: Optional collection name

    Returns:
        List of MCP servers

    Raises:
        HTTPException: On error
    """
    try:
        logger.info(f"Listing MCP servers (collection={collection})")

        # Get or create collection
        if collection:
            coll = collection_mgr.load_collection(collection)
        else:
            # Use default collection
            collections = collection_mgr.list_collections()
            if not collections:
                # No collections exist, return empty list
                return MCPServerListResponse(servers=[], total=0)
            coll = collection_mgr.load_collection(collections[0])

        # Get all MCP servers
        servers = coll.list_mcp_servers()

        # Convert to response format
        server_responses = [metadata_to_response(server) for server in servers]

        logger.info(f"Retrieved {len(server_responses)} MCP servers")
        return MCPServerListResponse(
            servers=server_responses,
            total=len(server_responses),
        )

    except Exception as e:
        logger.error(f"Error listing MCP servers: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list MCP servers: {str(e)}",
        )


@router.get(
    "/servers/{name}",
    response_model=MCPServerResponse,
    summary="Get MCP server details",
    description="Retrieve detailed information about a specific MCP server",
    responses={
        200: {"description": "Successfully retrieved server details"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Server not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def get_mcp_server(
    name: str,
    collection_mgr: CollectionManagerDep,
    token: TokenDep,
    collection: Optional[str] = Query(
        default=None,
        description="Collection name (uses default if not specified)",
    ),
) -> MCPServerResponse:
    """Get details for a specific MCP server.

    Args:
        name: Server name
        collection_mgr: Collection manager dependency
        token: Authentication token
        collection: Optional collection name

    Returns:
        MCP server details

    Raises:
        HTTPException: If server not found or on error
    """
    try:
        logger.info(f"Getting MCP server: {name} (collection={collection})")

        # Get or create collection
        if collection:
            coll = collection_mgr.load_collection(collection)
        else:
            collections = collection_mgr.list_collections()
            if not collections:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"No collections found",
                )
            coll = collection_mgr.load_collection(collections[0])

        # Find server
        server = coll.find_mcp_server(name)
        if not server:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"MCP server '{name}' not found",
            )

        return metadata_to_response(server)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting MCP server '{name}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get MCP server: {str(e)}",
        )


@router.post(
    "/servers",
    response_model=MCPServerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add new MCP server",
    description="Add a new MCP server to the collection",
    responses={
        201: {"description": "Server created successfully"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        409: {"model": ErrorResponse, "description": "Server already exists"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def create_mcp_server(
    request: MCPServerCreateRequest,
    collection_mgr: CollectionManagerDep,
    token: TokenDep,
    collection: Optional[str] = Query(
        default=None,
        description="Collection name (uses default if not specified)",
    ),
) -> MCPServerResponse:
    """Create a new MCP server in the collection.

    Args:
        request: Server creation request
        collection_mgr: Collection manager dependency
        token: Authentication token
        collection: Optional collection name

    Returns:
        Created MCP server details

    Raises:
        HTTPException: On error
    """
    try:
        logger.info(f"Creating MCP server: {request.name} (collection={collection})")

        # Get or create collection
        if collection:
            if collection not in collection_mgr.list_collections():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Collection '{collection}' not found",
                )
            coll = collection_mgr.load_collection(collection)
            collection_name = collection
        else:
            collections = collection_mgr.list_collections()
            if not collections:
                # Create default collection
                collection_name = "default"
                collection_mgr.create_collection(collection_name)
            else:
                collection_name = collections[0]
            coll = collection_mgr.load_collection(collection_name)

        # Create metadata
        try:
            server = MCPServerMetadata(
                name=request.name,
                repo=request.repo,
                version=request.version,
                env_vars=request.env_vars,
                description=request.description,
                status=MCPServerStatus.NOT_INSTALLED,
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid server metadata: {str(e)}",
            )

        # Add to collection
        try:
            coll.add_mcp_server(server)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(e),
            )

        # Save collection
        collection_mgr.save_collection(coll, collection_name)

        logger.info(f"Created MCP server '{request.name}' in collection '{collection_name}'")
        return metadata_to_response(server)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating MCP server: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create MCP server: {str(e)}",
        )


@router.put(
    "/servers/{name}",
    response_model=MCPServerResponse,
    summary="Update MCP server",
    description="Update an existing MCP server configuration",
    responses={
        200: {"description": "Server updated successfully"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Server not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def update_mcp_server(
    name: str,
    request: MCPServerUpdateRequest,
    collection_mgr: CollectionManagerDep,
    token: TokenDep,
    collection: Optional[str] = Query(
        default=None,
        description="Collection name (uses default if not specified)",
    ),
) -> MCPServerResponse:
    """Update an existing MCP server.

    Args:
        name: Server name
        request: Server update request
        collection_mgr: Collection manager dependency
        token: Authentication token
        collection: Optional collection name

    Returns:
        Updated MCP server details

    Raises:
        HTTPException: If server not found or on error
    """
    try:
        logger.info(f"Updating MCP server: {name} (collection={collection})")

        # Get collection
        if collection:
            coll = collection_mgr.load_collection(collection)
            collection_name = collection
        else:
            collections = collection_mgr.list_collections()
            if not collections:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No collections found",
                )
            collection_name = collections[0]
            coll = collection_mgr.load_collection(collection_name)

        # Find server
        server = coll.find_mcp_server(name)
        if not server:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"MCP server '{name}' not found",
            )

        # Update fields
        if request.repo is not None:
            server.repo = request.repo
        if request.version is not None:
            server.version = request.version
        if request.description is not None:
            server.description = request.description
        if request.env_vars is not None:
            server.env_vars = request.env_vars

        # Validate updated server
        try:
            server._validate_repo_url()
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid server configuration: {str(e)}",
            )

        # Save collection
        collection_mgr.save_collection(coll, collection_name)

        logger.info(f"Updated MCP server '{name}'")
        return metadata_to_response(server)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating MCP server '{name}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update MCP server: {str(e)}",
        )


@router.delete(
    "/servers/{name}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete MCP server",
    description="Remove an MCP server from the collection",
    responses={
        204: {"description": "Server deleted successfully"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Server not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def delete_mcp_server(
    name: str,
    collection_mgr: CollectionManagerDep,
    token: TokenDep,
    collection: Optional[str] = Query(
        default=None,
        description="Collection name (uses default if not specified)",
    ),
) -> None:
    """Delete an MCP server from the collection.

    Args:
        name: Server name
        collection_mgr: Collection manager dependency
        token: Authentication token
        collection: Optional collection name

    Raises:
        HTTPException: If server not found or on error
    """
    try:
        logger.info(f"Deleting MCP server: {name} (collection={collection})")

        # Get collection
        if collection:
            coll = collection_mgr.load_collection(collection)
            collection_name = collection
        else:
            collections = collection_mgr.list_collections()
            if not collections:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No collections found",
                )
            collection_name = collections[0]
            coll = collection_mgr.load_collection(collection_name)

        # Remove server
        if not coll.remove_mcp_server(name):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"MCP server '{name}' not found",
            )

        # Save collection
        collection_mgr.save_collection(coll, collection_name)

        logger.info(f"Deleted MCP server '{name}'")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting MCP server '{name}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete MCP server: {str(e)}",
        )


@router.post(
    "/servers/{name}/deploy",
    response_model=DeploymentResponse,
    summary="Deploy MCP server",
    description="Deploy MCP server to Claude Desktop settings.json",
    responses={
        200: {"description": "Server deployed successfully"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Server not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def deploy_mcp_server(
    name: str,
    request: DeploymentRequest,
    collection_mgr: CollectionManagerDep,
    config_mgr: ConfigManagerDep,
    token: TokenDep,
    collection: Optional[str] = Query(
        default=None,
        description="Collection name (uses default if not specified)",
    ),
) -> DeploymentResponse:
    """Deploy MCP server to Claude Desktop.

    Args:
        name: Server name
        request: Deployment request
        collection_mgr: Collection manager dependency
        config_mgr: Config manager dependency
        token: Authentication token
        collection: Optional collection name

    Returns:
        Deployment result

    Raises:
        HTTPException: If server not found or on error
    """
    try:
        logger.info(f"Deploying MCP server: {name} (dry_run={request.dry_run})")

        # Get collection
        if collection:
            coll = collection_mgr.load_collection(collection)
            collection_name = collection
        else:
            collections = collection_mgr.list_collections()
            if not collections:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No collections found",
                )
            collection_name = collections[0]
            coll = collection_mgr.load_collection(collection_name)

        # Find server
        server = coll.find_mcp_server(name)
        if not server:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"MCP server '{name}' not found",
            )

        # Get GitHub token if configured
        github_token = config_mgr.get("github-token")

        # Deploy server
        deployment_mgr = MCPDeploymentManager(github_token=github_token)
        result = deployment_mgr.deploy_server(
            server=server,
            dry_run=request.dry_run,
            backup=request.backup,
        )

        # Update collection if deployment succeeded and not dry run
        if result.success and not request.dry_run:
            collection_mgr.save_collection(coll, collection_name)

        # Build response
        if result.success:
            message = f"Server '{name}' deployed successfully"
            if request.dry_run:
                message = f"[DRY RUN] Server '{name}' would be deployed successfully"

            return DeploymentResponse(
                success=True,
                message=message,
                settings_path=str(result.settings_path) if result.settings_path else None,
                backup_path=str(result.backup_path) if result.backup_path else None,
                env_file_path=str(result.env_file_path) if result.env_file_path else None,
                command=result.command,
                args=result.args,
            )
        else:
            return DeploymentResponse(
                success=False,
                message=f"Deployment failed: {result.error_message}",
                error_message=result.error_message,
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deploying MCP server '{name}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deploy MCP server: {str(e)}",
        )


@router.post(
    "/servers/{name}/undeploy",
    response_model=DeploymentResponse,
    summary="Undeploy MCP server",
    description="Remove MCP server from Claude Desktop settings.json",
    responses={
        200: {"description": "Server undeployed successfully"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Server not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def undeploy_mcp_server(
    name: str,
    collection_mgr: CollectionManagerDep,
    config_mgr: ConfigManagerDep,
    token: TokenDep,
    collection: Optional[str] = Query(
        default=None,
        description="Collection name (uses default if not specified)",
    ),
) -> DeploymentResponse:
    """Undeploy MCP server from Claude Desktop.

    Args:
        name: Server name
        collection_mgr: Collection manager dependency
        config_mgr: Config manager dependency
        token: Authentication token
        collection: Optional collection name

    Returns:
        Undeploy result

    Raises:
        HTTPException: If server not found or on error
    """
    try:
        logger.info(f"Undeploying MCP server: {name}")

        # Get GitHub token if configured
        github_token = config_mgr.get("github-token")

        # Undeploy server
        deployment_mgr = MCPDeploymentManager(github_token=github_token)

        # Get settings path for response
        try:
            settings_path = deployment_mgr.get_settings_path()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get settings path: {str(e)}",
            )

        # Undeploy
        success = deployment_mgr.undeploy_server(name)

        if success:
            # Update server status in collection if it exists
            if collection:
                collection_name = collection
            else:
                collections = collection_mgr.list_collections()
                collection_name = collections[0] if collections else None

            if collection_name:
                try:
                    coll = collection_mgr.load_collection(collection_name)
                    server = coll.find_mcp_server(name)
                    if server:
                        server.status = MCPServerStatus.NOT_INSTALLED
                        collection_mgr.save_collection(coll, collection_name)
                except Exception as e:
                    logger.warning(f"Failed to update server status: {e}")

            return DeploymentResponse(
                success=True,
                message=f"Server '{name}' undeployed successfully",
                settings_path=str(settings_path),
            )
        else:
            return DeploymentResponse(
                success=False,
                message=f"Server '{name}' was not deployed",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error undeploying MCP server '{name}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to undeploy MCP server: {str(e)}",
        )


@router.get(
    "/servers/{name}/status",
    response_model=DeploymentStatusResponse,
    summary="Get deployment status",
    description="Check if MCP server is deployed to Claude Desktop",
    responses={
        200: {"description": "Successfully retrieved deployment status"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def get_deployment_status(
    name: str,
    config_mgr: ConfigManagerDep,
    token: TokenDep,
) -> DeploymentStatusResponse:
    """Get deployment status for an MCP server.

    Args:
        name: Server name
        config_mgr: Config manager dependency
        token: Authentication token

    Returns:
        Deployment status

    Raises:
        HTTPException: On error
    """
    try:
        logger.info(f"Getting deployment status for MCP server: {name}")

        # Get GitHub token if configured
        github_token = config_mgr.get("github-token")

        # Check deployment status
        deployment_mgr = MCPDeploymentManager(github_token=github_token)

        try:
            settings_path = deployment_mgr.get_settings_path()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get settings path: {str(e)}",
            )

        deployed = deployment_mgr.is_server_deployed(name)

        # Get server config if deployed
        command = None
        args = None
        if deployed:
            try:
                settings = deployment_mgr.read_settings()
                mcp_servers = settings.get("mcpServers", {})
                server_config = mcp_servers.get(name, {})
                command = server_config.get("command")
                args = server_config.get("args")
            except Exception as e:
                logger.warning(f"Failed to read server config: {e}")

        return DeploymentStatusResponse(
            deployed=deployed,
            settings_path=str(settings_path),
            last_deployed=None,  # Would need to track this separately
            health_status="unknown",  # Would need health check implementation
            command=command,
            args=args,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting deployment status for '{name}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get deployment status: {str(e)}",
        )
