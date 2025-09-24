# /// script
# requires-python = ">=3.13"
# dependencies = []
# ///

"""
MCP Server for Cursor integration with MemMachine.

This server provides memory CRUD operations to Cursor through MCP protocol,
communicating with MemMachine service via HTTP requests.
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastmcp import FastMCP
from fastmcp.server.dependencies import get_http_request
from pydantic import BaseModel, Field

# =============================================================================
# Configuration and Constants
# =============================================================================

# Environment Configuration
MEMORY_BACKEND_URL: str = os.getenv("MEMORY_BACKEND_URL", "http://localhost:8080")
CURSOR_MCP_PORT: int = int(os.getenv("CURSOR_MCP_PORT", "8001"))

# Session Configuration Constants
DEFAULT_GROUP_ID: Optional[str] = None
DEFAULT_AGENT_ID: List[str] = ["cursor_assistant"]
DEFAULT_PRODUCER: str = "cursor_user"
DEFAULT_PRODUCED_FOR: str = "cursor_assistant"
DEFAULT_EPISODE_TYPE: str = "message"

# HTTP Configuration
REQUEST_TIMEOUT: int = 30

# =============================================================================
# Logging Configuration
# =============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# =============================================================================
# MCP Server Initialization
# =============================================================================

mcp = FastMCP("CursorMemMachine")



# =============================================================================
# Data Models
# =============================================================================

class SessionData(BaseModel):
    """Session data model for MemMachine requests."""
    
    group_id: Optional[str] = Field(
        DEFAULT_GROUP_ID, 
        description="Group ID for the session"
    )
    agent_id: List[str] = Field(
        DEFAULT_AGENT_ID, 
        description="List of agent IDs"
    )
    user_id: List[str] = Field(
        ..., 
        description="List of user IDs"
    )
    session_id: str = Field(
        ..., 
        description="Unique session identifier"
    )


class MemoryEpisode(BaseModel):
    """Memory episode data model."""
    
    session: SessionData = Field(
        ..., 
        description="Session data for the memory"
    )
    producer: str = Field(
        ..., 
        description="Who produced the memory"
    )
    produced_for: str = Field(
        ..., 
        description="Who the memory is produced for"
    )
    episode_content: str = Field(
        ..., 
        description="The actual memory content"
    )
    episode_type: str = Field(
        DEFAULT_EPISODE_TYPE, 
        description="Type of the memory episode"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None, 
        description="Additional metadata for the memory"
    )


class SearchQuery(BaseModel):
    """Search query model."""
    
    session: SessionData = Field(
        ..., 
        description="Session data for the search"
    )
    query: str = Field(
        ..., 
        description="The search query string"
    )
    limit: Optional[int] = Field(
        5, 
        description="Maximum number of results to return"
    )
    filter: Optional[Dict[str, Any]] = Field(
        None, 
        description="Optional filters for the search"
    )


class DeleteRequest(BaseModel):
    """Delete request model."""
    
    session: SessionData = Field(
        ..., 
        description="Session data to delete"
    )


# =============================================================================
# Utility Functions and Classes
# =============================================================================

class MemMachineClient:
    """HTTP client for MemMachine API operations."""
    
    def __init__(self, base_url: str, timeout: int = REQUEST_TIMEOUT):
        """Initialize the MemMachine client.
        
        Args:
            base_url: Base URL for the MemMachine API
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.logger = logging.getLogger(f"{__name__}.MemMachineClient")
    
    def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make an HTTP request to the MemMachine API.
        
        Args:
            method: HTTP method (GET, POST, DELETE, etc.)
            endpoint: API endpoint path
            data: Request data for POST/PUT requests
            
        Returns:
            Response data as dictionary
            
        Raises:
            requests.exceptions.RequestException: For HTTP errors
            Exception: For other errors
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            self.logger.debug(f"Making {method} request to {url}")
            if data:
                self.logger.debug(f"Request data: {data}")
            
            response = requests.request(
                method=method,
                url=url,
                json=data,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            return response.json() if response.content else {}
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"HTTP error in {method} {url}: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error in {method} {url}: {e}")
            raise
    
    def add_memory(self, episode_data: MemoryEpisode) -> Dict[str, Any]:
        """Add a memory episode to MemMachine.
        
        Args:
            episode_data: Memory episode data
            
        Returns:
            Response data from the API
        """
        return self._make_request(
            method="POST",
            endpoint="/v1/memories",
            data=episode_data.model_dump()
        )
    
    def search_memory(self, search_data: SearchQuery) -> Dict[str, Any]:
        """Search for memories in MemMachine.
        
        Args:
            search_data: Search query data
            
        Returns:
            Search results from the API
        """
        return self._make_request(
            method="POST",
            endpoint="/v1/memories/search",
            data=search_data.model_dump()
        )
    
    def delete_session_memory(self, delete_data: DeleteRequest) -> Dict[str, Any]:
        """Delete all memories for a session.
        
        Args:
            delete_data: Delete request data
            
        Returns:
            Response data from the API
        """
        return self._make_request(
            method="DELETE",
            endpoint="/v1/memories",
            data=delete_data.model_dump()
        )


def create_error_response(
    status: str, 
    message: str, 
    error_type: Optional[str] = None
) -> Dict[str, Any]:
    """Create a standardized error response.
    
    Args:
        status: Error status
        message: Error message
        error_type: Optional error type
        
    Returns:
        Standardized error response dictionary
    """
    response = {
        "status": status,
        "message": message
    }
    if error_type:
        response["error_type"] = error_type
    return response


def create_success_response(
    message: str, 
    **kwargs
) -> Dict[str, Any]:
    """Create a standardized success response.
    
    Args:
        message: Success message
        **kwargs: Additional response data
        
    Returns:
        Standardized success response dictionary
    """
    response = {
        "status": "success",
        "message": message
    }
    response.update(kwargs)
    return response


def extract_session_headers(request: Request) -> tuple[Optional[str], Optional[str]]:
    """Extract user_id and session_id from request headers.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Tuple of (user_id, session_id)
    """
    user_id = (
        request.headers.get("user-id") or 
        request.headers.get("User-ID") or 
        request.headers.get("USER-ID")
    )
    session_id = (
        request.headers.get("mcp-session-id") or 
        request.headers.get("Mcp-Session-Id") or 
        request.headers.get("MCP-SESSION-ID")
    )
    return user_id, session_id


def create_session_data(user_id: str, session_id: Optional[str] = None) -> SessionData:
    """Create session data for MemMachine requests.
    
    Args:
        user_id: User identifier
        session_id: Optional session identifier
        
    Returns:
        SessionData object
    """
    return SessionData(
        group_id=DEFAULT_GROUP_ID,
        agent_id=DEFAULT_AGENT_ID,
        user_id=[user_id],
        session_id=session_id
    )


# Initialize MemMachine client
memmachine_client = MemMachineClient(MEMORY_BACKEND_URL)



# =============================================================================
# MCP Tool Functions
# =============================================================================

@mcp.tool()
async def add_memory(
    content: str = Field(..., description="The memory content to store"),
) -> Dict[str, Any]:
    """
    Add a memory episode to MemMachine.
    
    Args:
        content: The memory content to store
    
    Returns:
        Dictionary with status and message
    """
    try:
        # Extract session information from request headers
        request: Request = get_http_request()
        user_id, session_id = extract_session_headers(request)
        
        logger.info(f"Adding memory - Content: {content[:100]}...")
        logger.info(f"User ID: {user_id}, Session ID: {session_id}")
        
        # Validate required headers
        if not user_id:
            logger.error("User ID not provided in headers")
            return create_error_response(
                "error", 
                "User ID is required in request headers"
            )
        
        # Create session and episode data
        session_data = create_session_data(user_id, session_id)
        
        episode_data = MemoryEpisode(
            session=session_data,
            episode_content=content,    
            producer=user_id,
            produced_for=DEFAULT_PRODUCED_FOR,
            episode_type=DEFAULT_EPISODE_TYPE,
            metadata={
                "speaker": user_id,
                "timestamp": datetime.now().isoformat(),
                "type": "message",
            }
        )
        
        # Add memory using the client
        memmachine_client.add_memory(episode_data)
        
        logger.info(f"Successfully added memory for user {user_id}")
        return create_success_response(
            "Memory added successfully",
            session_id=session_id,
            user_id=user_id
        )
        
    except requests.exceptions.RequestException as e:
        logger.error(f"HTTP error adding memory: {e}")
        return create_error_response(
            "error", 
            f"Failed to add memory: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error adding memory: {e}")
        return create_error_response(
            "error", 
            f"Internal error: {str(e)}"
        )


@mcp.tool()
async def search_memory(
    query: str = Field(..., description="The search query"),
    limit: int = Field(5, description="Maximum number of results to return"),
) -> Dict[str, Any]:
    """
    Search for memories in MemMachine.
    
    Args:
        query: The search query
        limit: Maximum number of results to return
    
    Returns:
        Dictionary with search results
    """
    try:
        # Extract session information from request headers
        request: Request = get_http_request()
        user_id, session_id = extract_session_headers(request)
        
        logger.info(f"Searching memory - Query: {query[:100]}...")
        logger.info(f"User ID: {user_id}, Session ID: {session_id}, Limit: {limit}")
        
        # Validate required headers
        if not user_id:
            return create_error_response(
                "error", 
                "User ID is required in request headers"
            )
        
        # Create session and search data
        session_data = create_session_data(user_id, session_id)
        
        search_data = SearchQuery(
            session=session_data,
            query=query,
            limit=limit
        )
        
        # Search memory using the client
        result = memmachine_client.search_memory(search_data)
        
        # Extract and format results
        content = result.get("content", {})
        episodic_memory = content.get("episodic_memory", [])
        profile_memory = content.get("profile_memory", [])
        
        logger.info(f"Search completed - Found {len(episodic_memory)} episodic, {len(profile_memory)} profile memories")
        
        return create_success_response(
            "Search completed successfully",
            session_id=session_id,
            user_id=user_id,
            query=query,
            results={
                "episodic_memory": episodic_memory,
                "profile_memory": profile_memory
            },
            total_results=len(episodic_memory) + len(profile_memory)
        )
        
    except requests.exceptions.RequestException as e:
        logger.error(f"HTTP error searching memory: {e}")
        return create_error_response(
            "error", 
            f"Failed to search memory: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error searching memory: {e}")
        return create_error_response(
            "error", 
            f"Internal error: {str(e)}"
        )


@mcp.tool()
async def delete_session_memory() -> Dict[str, Any]:
    """
    Delete all memories for the current session.
    
    Returns:
        Dictionary with status and message
    """
    try:
        # Extract session information from request headers
        request: Request = get_http_request()
        user_id, session_id = extract_session_headers(request)
        
        logger.info(f"Deleting session memory - User ID: {user_id}, Session ID: {session_id}")
        
        # Validate required headers
        if not user_id or not session_id:
            return create_error_response(
                "error", 
                "User ID and Session ID are required in request headers"
            )
        
        # Create session and delete request data
        session_data = create_session_data(user_id, session_id)
        delete_request = DeleteRequest(session=session_data)
        
        # Delete session memory using the client
        memmachine_client.delete_session_memory(delete_request)
        
        logger.info(f"Successfully deleted session {session_id} for user {user_id}")
        return create_success_response(
            f"Session {session_id} deleted successfully",
            session_id=session_id,
            user_id=user_id
        )
        
    except requests.exceptions.RequestException as e:
        logger.error(f"HTTP error deleting session: {e}")
        return create_error_response(
            "error", 
            f"Failed to delete session: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error deleting session: {e}")
        return create_error_response(
            "error", 
            f"Internal error: {str(e)}"
        )




# =============================================================================
# Middleware and Application Setup
# =============================================================================

class SessionMiddleware:
    """Middleware for session management and request logging."""
    
    def __init__(self, app):
        self.app = app
        self.logger = logging.getLogger(f"{__name__}.SessionMiddleware")
    
    async def __call__(self, request: Request, call_next):
        """Process request with session management and logging."""
        # Log request details
        self._log_request_details(request)
        
        # Extract session information
        user_id, session_id = extract_session_headers(request)
        
        # Log request body for POST requests
        if request.method == "POST":
            await self._log_request_body(request)
        
        try:
            response = await call_next(request)
            
            # Log response details
            self._log_response_details(response)
            
            # Set session ID in response headers if available
            if session_id:
                response.headers["Mcp-Session-Id"] = session_id
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error in request processing: {e}")
            self.logger.error(f"Error type: {type(e).__name__}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "message": str(e),
                    "type": type(e).__name__
                }
            )
    
    def _log_request_details(self, request: Request) -> None:
        """Log request details for debugging."""
        self.logger.info("=== MCP Server Request Debug ===")
        self.logger.info(f"Request URL: {request.url}")
        self.logger.info(f"Request Method: {request.method}")
        self.logger.info(f"Request Path: {request.url.path}")
        self.logger.info("All Headers:")
        for header_name, header_value in request.headers.items():
            self.logger.info(f"  {header_name}: {header_value}")
    
    async def _log_request_body(self, request: Request) -> None:
        """Log request body for POST requests."""
        try:
            body = await request.body()
            if body:
                try:
                    data = json.loads(body)
                    self.logger.info(f"Request body: {json.dumps(data, indent=2)}")
                except json.JSONDecodeError:
                    self.logger.info(f"Request body (raw): {body.decode('utf-8', errors='ignore')}")
            else:
                self.logger.info("Request body: (empty)")
        except Exception as e:
            self.logger.error(f"Error reading request body: {e}")
    
    def _log_response_details(self, response) -> None:
        """Log response details."""
        self.logger.info(f"Response status: {response.status_code}")
        self.logger.info("Response headers:")
        for header_name, header_value in response.headers.items():
            self.logger.info(f"  {header_name}: {header_value}")
        self.logger.info("=== End Request Debug ===")


def create_custom_app() -> FastAPI:
    """Create a custom FastAPI app with session management.
    
    Returns:
        Configured FastAPI application
    """
    # Create MCP app first to get its lifespan
    mcp_app = mcp.http_app("/")
    logger.info("MCP app created successfully")
    
    # Create FastAPI app with MCP lifespan
    app = FastAPI(
        title="Cursor MCP Server",
        description="MCP Server for Cursor integration with MemMachine",
        version="1.0.0",
        lifespan=mcp_app.lifespan
    )
    logger.info("FastAPI app created successfully")
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add session middleware
    app.middleware("http")(SessionMiddleware(app))
    
    # Add health check endpoint
    @app.get("/health")
    async def health_check() -> Dict[str, str]:
        """Simple health check endpoint."""
        return {
            "status": "healthy", 
            "message": "Cursor MCP Server is running"
        }
    
    # Add debug endpoint
    @app.get("/debug")
    async def debug_info() -> Dict[str, Any]:
        """Debug endpoint to show server configuration."""
        return {
            "server": "Cursor MCP Server",
            "memory_backend_url": MEMORY_BACKEND_URL,
            "port": CURSOR_MCP_PORT,
            "mcp_endpoint": "/mcp",
            "health_endpoint": "/health"
        }
    
    # Mount the MCP app
    logger.info("Mounting MCP app at /mcp")
    app.mount("/mcp", mcp_app)
    logger.info("MCP app mounted successfully")
    
    return app

# =============================================================================
# Application Entry Point
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    logger.info("=" * 60)
    logger.info("Starting Cursor MCP Server")
    logger.info("=" * 60)
    logger.info(f"Port: {CURSOR_MCP_PORT}")
    logger.info(f"MemMachine Backend URL: {MEMORY_BACKEND_URL}")
    logger.info(f"Request Timeout: {REQUEST_TIMEOUT}s")
    logger.info("=" * 60)
    
    # Create custom app with session management
    app = create_custom_app()
    
    # Start the server
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=CURSOR_MCP_PORT,
        log_level="info"
    )

