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
from datetime import datetime, timedelta
import secrets
from threading import Lock
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
MEMORY_BACKEND_URL: str = os.getenv("MEMORY_BACKEND_URL", "https://ec2-35-77-228-181.ap-northeast-1.compute.amazonaws.com/memmachine")
# MEMORY_BACKEND_URL: str = os.getenv("MEMORY_BACKEND_URL", "http://localhost:8080")
CURSOR_MCP_PORT: int = int(os.getenv("CURSOR_MCP_PORT", "8001"))
# SSL verification setting for self-signed certificates
VERIFY_SSL: bool = os.getenv("VERIFY_SSL", "false").lower() in ("true", "1", "yes", "on")
# Optional auth token. If set, all requests must include it
MCP_AUTH_TOKEN: Optional[str] = os.getenv("MCP_AUTH_TOKEN") or None
AUTH_USERNAME: Optional[str] = os.getenv("AUTH_USERNAME") or None
AUTH_PASSWORD: Optional[str] = os.getenv("AUTH_PASSWORD") or None
TOKEN_TTL_SECONDS: int = int(os.getenv("TOKEN_TTL_SECONDS", "3600"))

# Session Configuration Constants
DEFAULT_GROUP_ID: Optional[str] = None
DEFAULT_AGENT_ID: List[str] = ["cursor_assistant"]
DEFAULT_SESSION_ID: str = "cursor_session"
DEFAULT_USER_ID: str = "cursor_user"
DEFAULT_PRODUCER: str = "cursor_user"
DEFAULT_PRODUCED_FOR: str = "cursor_assistant"
DEFAULT_EPISODE_TYPE: str = "message"

# HTTP Configuration
REQUEST_TIMEOUT: int = 30

# =============================================================================
# Logging Configuration
# =============================================================================

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(filename)s:%(lineno)d - %(levelname)s - %(message)s',
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
    agent_id: Optional[List[str]] = Field(
        DEFAULT_AGENT_ID, 
        description="List of agent IDs"
    )
    user_id: Optional[List[str]] = Field(
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

class InMemoryTokenStore:
    """Simple in-memory token store with expiration."""
    
    def __init__(self, default_ttl_seconds: int = 3600):
        self._tokens: Dict[str, Dict[str, Any]] = {}
        self._lock = Lock()
        self._default_ttl_seconds = default_ttl_seconds
        self.logger = logging.getLogger(f"{__name__}.InMemoryTokenStore")
    
    def issue_token(self, subject: str, ttl_seconds: Optional[int] = None) -> Dict[str, Any]:
        now = datetime.now()
        ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl_seconds
        expires_at = now + timedelta(seconds=ttl)
        token = secrets.token_urlsafe(32)
        with self._lock:
            self._tokens[token] = {
                "subject": subject,
                "issued_at": now.isoformat(),
                "expires_at": expires_at.isoformat(),
            }
        return {"token": token, "expires_at": expires_at.isoformat(), "subject": subject}
    
    def validate_token(self, token: Optional[str]) -> bool:
        if not token:
            return False
        with self._lock:
            data = self._tokens.get(token)
            if not data:
                return False
            try:
                if datetime.fromisoformat(data["expires_at"]) < datetime.now():
                    # expired, remove
                    self._tokens.pop(token, None)
                    return False
            except Exception:
                # if parsing fails, revoke token defensively
                self._tokens.pop(token, None)
                return False
            return True
    
    def revoke_token(self, token: Optional[str]) -> bool:
        if not token:
            return False
        with self._lock:
            return self._tokens.pop(token, None) is not None
    
    def cleanup_expired(self) -> int:
        removed = 0
        now = datetime.now()
        with self._lock:
            to_delete = [t for t, d in self._tokens.items() if datetime.fromisoformat(d.get("expires_at", "1970-01-01T00:00:00")) < now]
            for t in to_delete:
                self._tokens.pop(t, None)
                removed += 1
        if removed:
            self.logger.info(f"Token cleanup removed {removed} expired tokens")
        return removed

class MemMachineClient:
    """HTTP client for MemMachine API operations."""
    
    def __init__(self, base_url: str, timeout: int = REQUEST_TIMEOUT, verify_ssl: bool = True):
        """Initialize the MemMachine client.
        
        Args:
            base_url: Base URL for the MemMachine API
            timeout: Request timeout in seconds
            verify_ssl: Whether to verify SSL certificates (default: True)
                       Set to False for self-signed certificates
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.logger = logging.getLogger(f"{__name__}.MemMachineClient")
        
        # Log SSL verification setting for debugging
        if not self.verify_ssl:
            self.logger.warning("SSL certificate verification is DISABLED. This should only be used for development/testing with self-signed certificates.")
    
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
                timeout=self.timeout,
                verify=self.verify_ssl
            )
            response.raise_for_status()
            
            return response.json() if response.content else {}
        except requests.exceptions.HTTPError as e:
            self.logger.error(f"HTTP error in {method} {url}: {e}")
            raise
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
        self.logger.info(f"Adding memory - Episode data: {episode_data.model_dump()}")
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


async def _fetch_profile_memory(user_id: str, session_id: str, limit: int) -> Dict[str, Any]:
    """Fetch profile memory items for a given user and session.
    
    This internal helper consolidates the logic to construct the session and
    search requests and extracts the profile memory content from the result.
    """
    session_data = create_session_data(session_id=session_id, user_id=user_id)
    search_data = SearchQuery(session=session_data, query="", limit=limit, filter=None)
    result = memmachine_client.search_memory(search_data)
    content = result.get("content", {})
    profile_memory = content.get("profile_memory", [])
    
    logger.info(f"Profile memory retrieval completed - Found {len(profile_memory)} profile memories")
    
    # Format profile memory data for better readability
    formatted_profile_memory = []
    for memory in profile_memory:
        formatted_memory = {
            "id": memory.get("metadata", {}).get("id", "unknown"),
            "similarity_score": memory.get("metadata", {}).get("similarity_score", 0.0),
            "tag": memory.get("tag", ""),
            "feature": memory.get("feature", ""),
            "value": memory.get("value", ""),
        }
        formatted_profile_memory.append(formatted_memory)
    
    return create_success_response(
        "Profile memory retrieved successfully",
        session_id=session_id,
        user_id=user_id,
        profile_memory=formatted_profile_memory,
        total_profile_memories=len(formatted_profile_memory),
        limit_requested=limit
    )

def _real_format_episodic_memory(memory: Dict[str, Any]) -> Dict[str, Any]:
    """Format episodic memory data for better readability."""
    logger.info(f"Formatting episodic memory: {memory}")
    formatted_memory = {
        "uuid": memory.get("uuid", "unknown"),
        "episode_type": memory.get("episode_type", "message"),
        "content_type": memory.get("content_type", "string"),
        "content": memory.get("content", ""),
        "timestamp": memory.get("timestamp", ""),
        "group_id": memory.get("group_id", "unknown"),
        "session_id": memory.get("session_id", "unknown"),
        "producer_id": memory.get("producer_id", "unknown"),
        "produced_for_id": memory.get("produced_for_id", "unknown"),
        "user_metadata": memory.get("user_metadata", {}),
    }
    return formatted_memory

def _format_episodic_memory(memory) -> Optional[List[Dict[str, Any]]]:
    formatted_episodic_memory = []
    if isinstance(memory, list):
        for m in memory:
            formatted_memory = _format_episodic_memory(m)
            if formatted_memory:
                formatted_episodic_memory.extend(formatted_memory)
    elif isinstance(memory, dict):
        formatted_memory = _real_format_episodic_memory(memory)
        if formatted_memory:
            formatted_episodic_memory.append(formatted_memory)
    else:
        logger.warning(f"Unknown episodic memory type: {type(memory)}")
    return formatted_episodic_memory

async def _fetch_episodic_memory(user_id: str, session_id: str, limit: int) -> Dict[str, Any]:
    """Fetch episodic memory items for a given user and session.
    
    This internal helper consolidates the logic to construct the session and
    search requests and extracts the episodic memory content from the result.
    """
    session_data = create_session_data(session_id=session_id, user_id=user_id)
    search_data = SearchQuery(session=session_data, query="", limit=limit, filter=None)
    result = memmachine_client.search_memory(search_data)

    logger.info(f"Episodic memory retrieval completed - Found {len(result)} episodic memories, data: {result}")

    # Extract episodic memory from the search results
    content = result.get("content", {})
    episodic_memory = content.get("episodic_memory", [])
    
    logger.info(f"Episodic memory retrieval completed - Found {len(episodic_memory)} episodic memories")
    
    # Format episodic memory data for better readability
    formatted_episodic_memory = []
    for memory in episodic_memory:
        logger.info(f"Episodic memory: {memory}")
        formatted_memory = _format_episodic_memory(memory)
        if formatted_memory:
            formatted_episodic_memory.extend(formatted_memory)
    
    return create_success_response(
        "Episodic memory retrieved successfully",
        session_id=session_id,
        user_id=user_id,
        episodic_memory=formatted_episodic_memory,
        total_episodic_memories=len(formatted_episodic_memory),
        limit_requested=limit
    )


async def _handle_add_memory(user_id: str, session_id: str, content: str) -> Dict[str, Any]:
    """Handle adding a memory episode using resolved user and session ids.

    This helper centralizes the core logic so both MCP tools and REST endpoints
    can reuse it without duplicating implementation details.
    """
    session_data = create_session_data(session_id=session_id, user_id=user_id)
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
        },
    )
    memmachine_client.add_memory(episode_data)
    return create_success_response("Memory added successfully", session_id=session_id, user_id=user_id)


async def _handle_search_memory(user_id: str, session_id: str, query: str, limit: int) -> Dict[str, Any]:
    """Handle memory search with unified logic for both MCP and REST callers."""
    session_data = create_session_data(user_id, session_id)
    search_data = SearchQuery(session=session_data, query=query, limit=limit, filter=None)
    result = memmachine_client.search_memory(search_data)
    content = result.get("content", {})
    episodic_memory = content.get("episodic_memory", [])
    profile_memory = content.get("profile_memory", [])
    return create_success_response(
        "Search completed successfully",
        session_id=session_id,
        user_id=user_id,
        query=query,
        results={
            "episodic_memory": episodic_memory,
            "profile_memory": profile_memory,
        },
        total_results=len(episodic_memory) + len(profile_memory),
    )


async def _handle_delete_session_memory(user_id: str, session_id: str) -> Dict[str, Any]:
    """Handle session memory deletion with unified logic for both MCP and REST callers."""
    if not session_id:
        return create_error_response("error", "Session ID is required for delete operation")
    session_data = create_session_data(user_id, session_id)
    delete_request = DeleteRequest(session=session_data)
    memmachine_client.delete_session_memory(delete_request)
    return create_success_response(f"Session {session_id} deleted successfully", session_id=session_id, user_id=user_id)

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


def extract_session_headers(request: Request) -> tuple[str, str]:
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
    if not user_id:
        logger.warning(f"User ID not provided in headers, using default: {DEFAULT_USER_ID}")
        user_id = DEFAULT_USER_ID
    session_id = (
        request.headers.get("mcp-session-id") or 
        request.headers.get("Mcp-Session-Id") or 
        request.headers.get("MCP-SESSION-ID")
    )
    if not session_id:
        logger.warning(f"Session ID not provided in headers, using default: {DEFAULT_SESSION_ID}")
        session_id = DEFAULT_SESSION_ID
    logger.debug(f"Extracted session info - User ID: {user_id}, Session ID: {session_id}")
    return user_id, session_id


def create_session_data(session_id: str, user_id: Optional[str] = None) -> SessionData:
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
        user_id=[DEFAULT_USER_ID],
        session_id=DEFAULT_SESSION_ID
    )
    # return SessionData(
    #     group_id=DEFAULT_GROUP_ID,
    #     agent_id=DEFAULT_AGENT_ID,
    #     user_id=[user_id] if user_id else None,
    #     session_id=session_id
    # )


# Initialize MemMachine client with SSL verification setting
memmachine_client = MemMachineClient(MEMORY_BACKEND_URL, verify_ssl=VERIFY_SSL)
token_store = InMemoryTokenStore(TOKEN_TTL_SECONDS)



# =============================================================================
# MCP Tool Functions
# =============================================================================

@mcp.tool()
async def mcp_add_memory(
    content: str = Field(..., description="The memory content to store"),
    memory_session_id: str = Field(..., description="Explicit memory session id provided by the caller")
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
        header_user_id, header_session_id = extract_session_headers(request)
        
        logger.info(f"Adding memory - Content: {content[:100]}...")
        # Prefer explicit parameter for session id
        user_id = header_user_id or DEFAULT_USER_ID
        session_id = memory_session_id or header_session_id

        logger.info(f"User ID: {user_id}, Session ID: {session_id}")
        
        # Create session and episode via unified handler
        result = await _handle_add_memory(user_id=user_id, session_id=session_id, content=content)
        logger.info(f"Successfully added memory for user {user_id}")
        return result
        
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
async def mcp_search_memory(
    query: str = Field(..., description="The search query"),
    limit: int = Field(..., description="Maximum number of results to return"),
    memory_session_id: str = Field(..., description="Explicit memory session id provided by the caller"),
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
        header_user_id, header_session_id = extract_session_headers(request)
        
        logger.info(f"Searching memory - Query: {query[:100]}...")
        user_id = header_user_id or DEFAULT_USER_ID
        session_id = memory_session_id or header_session_id
        logger.info(f"User ID: {user_id}, Session ID: {session_id}, Limit: {limit}")
        
        # Unified search handler
        result = await _handle_search_memory(user_id=user_id, session_id=session_id, query=query, limit=limit)
        logger.info("Search completed via unified handler")
        return result
        
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
async def mcp_delete_session_memory(
    memory_session_id: str = Field(..., description="Explicit memory session id provided by the caller")
) -> Dict[str, Any]:
    """
    Delete all memories for the current session.
    
    Returns:
        Dictionary with status and message
    """
    try:
        # Extract session information from request headers
        request: Request = get_http_request()
        header_user_id, header_session_id = extract_session_headers(request)
        
        user_id = header_user_id or DEFAULT_USER_ID
        session_id = memory_session_id or header_session_id
        logger.info(f"Deleting session memory - User ID: {user_id}, Session ID: {session_id}")
        
        result = await _handle_delete_session_memory(user_id=user_id, session_id=session_id)
        logger.info(f"Successfully deleted session {session_id} for user {user_id}")
        return result
        
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

@mcp.tool()
async def mcp_get_profile_memory(
    limit: int = Field(..., description="Maximum number of profile memories to return"),
    memory_session_id: str = Field(..., description="Explicit memory session id provided by the caller")
) -> Dict[str, Any]:
    """
    Get the profile memory for the current session.
    
    This function retrieves user profile information stored in MemMachine,
    including user preferences, facts, and personalized data that persists
    across multiple sessions and interactions.
    
    Args:
        limit: Maximum number of profile memories to return (default: 10)
    
    Returns:
        Dictionary containing profile memory data and metadata
    """
    try:
        # Extract session information from request headers
        request: Request = get_http_request()
        header_user_id, header_session_id = extract_session_headers(request)
        
        user_id = header_user_id or DEFAULT_USER_ID
        session_id = memory_session_id or header_session_id
        logger.info(f"Retrieving profile memory - User ID: {user_id}, Session ID: {session_id}, Limit: {limit}")

        return await _fetch_profile_memory(user_id=user_id, session_id=session_id, limit=limit)
        
    except requests.exceptions.RequestException as e:
        logger.error(f"HTTP error retrieving profile memory: {e}")
        return create_error_response(
            "error", 
            f"Failed to retrieve profile memory: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error retrieving profile memory: {e}")
        return create_error_response(
            "error", 
            f"Internal error: {str(e)}"
        )

@mcp.tool()
async def mcp_get_episodic_memory(
    limit: int = Field(..., description="Maximum number of episodic memories to return"),
    memory_session_id: str = Field(..., description="Explicit memory session id provided by the caller")
) -> Dict[str, Any]:
    """
    Get the episodic memory for the current session.
    
    This function retrieves conversation episodes and contextual memories
    stored in MemMachine, including recent interactions, conversation history,
    and session-specific context that helps maintain continuity across
    multiple interactions.
    
    Args:
        limit: Maximum number of episodic memories to return (default: 10)
    
    Returns:
        Dictionary containing episodic memory data and metadata
    """
    try:
        # Extract session information from request headers
        request: Request = get_http_request()
        header_user_id, header_session_id = extract_session_headers(request)
        
        user_id = header_user_id or DEFAULT_USER_ID
        session_id = memory_session_id or header_session_id
        logger.info(f"Retrieving episodic memory - User ID: {user_id}, Session ID: {session_id}, Limit: {limit}")
        
        return await _fetch_episodic_memory(user_id=user_id, session_id=session_id, limit=limit)
        
    except requests.exceptions.RequestException as e:
        logger.error(f"HTTP error retrieving episodic memory: {e}")
        return create_error_response(
            "error", 
            f"Failed to retrieve episodic memory: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error retrieving episodic memory: {e}")
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
        # Exempt some public endpoints from auth
        path = request.url.path
        if path in {"/health", "/debug", "/auth/login"}:
            return await call_next(request)
        
        # Enforce token authentication if configured or token-based auth is enabled
        provided_token: Optional[str] = None
        auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            provided_token = auth_header[len("Bearer "):].strip()
        if not provided_token:
            provided_token = request.headers.get("x-mcp-token") or request.headers.get("X-MCP-Token")
        if not provided_token:
            provided_token = request.headers.get("api_key") or request.headers.get("API_KEY")
        
        allow_via_env = MCP_AUTH_TOKEN and provided_token == MCP_AUTH_TOKEN
        allow_via_store = token_store.validate_token(provided_token)
        if MCP_AUTH_TOKEN or allow_via_store:
            if not (allow_via_env or allow_via_store):
                self.logger.warning("Unauthorized request blocked (invalid or missing token)")
                return JSONResponse(
                    status_code=401,
                    content={
                        "error": "Unauthorized",
                        "message": "Missing or invalid token",
                    },
                    headers={"WWW-Authenticate": "Bearer"}
                )
        # Log request details
        self._log_request_details(request)
        
        # Extract session information
        user_id, session_id = extract_session_headers(request)
        
        # Log request body for POST requests
        if request.method == "POST":
            await self._log_request_body(request)
        
        try:
            response = await call_next(request)

            response_session_id = response.headers.get("Mcp-Session-Id", None)
            
            # Log response details
            self._log_response_details(response)
            
            # Set session ID in response headers if available
            if response_session_id:
                response.headers["Mcp-Session-Id"] = response_session_id
            
            # Wrap streaming responses to capture content
            if (hasattr(response, 'body_iterator') and 
                hasattr(response.body_iterator, '__aiter__')):
                response = self._wrap_streaming_response(response)
            
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
            lower_name = header_name.lower()
            if lower_name in {"authorization", "x-mcp-token"}:
                masked_value = "***redacted***"
                self.logger.info(f"  {header_name}: {masked_value}")
            else:
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
        
        # Log response body - handle different response types
        try:
            # For streaming responses, we can't easily read the body
            if hasattr(response, 'body') and response.body:
                try:
                    # Try to parse as JSON for better formatting
                    body_data = json.loads(response.body)
                    self.logger.info(f"Response body: {json.dumps(body_data, indent=2)}")
                except (json.JSONDecodeError, TypeError):
                    # If not JSON, log as text
                    body_text = response.body.decode('utf-8', errors='ignore') if isinstance(response.body, bytes) else str(response.body)
                    self.logger.info(f"Response body: {body_text}")
            else:
                # For streaming responses, try to read the body content
                content_length = response.headers.get("content-length")
                if content_length and int(content_length) > 0:
                    try:
                        # Try to read the streaming response body
                        if hasattr(response, 'body_iterator'):
                            # For streaming responses with body_iterator (async generator)
                            try:
                                import asyncio
                                body_chunks = []
                                
                                # Check if it's an async generator
                                if hasattr(response.body_iterator, '__aiter__'):
                                    # For async generators, we'll wrap them to log content
                                    self.logger.info(f"Response body: (async generator streaming, {content_length} bytes)")
                                    self.logger.info(f"Generator type: {type(response.body_iterator)}")
                                    self.logger.info("Async generator will be wrapped for content logging")
                                else:
                                    # Handle regular iterator
                                    for chunk in response.body_iterator:
                                        if chunk:
                                            body_chunks.append(chunk)
                                
                                if body_chunks:
                                    body_content = b''.join(body_chunks)
                                    body_text = body_content.decode('utf-8', errors='ignore')
                                    self.logger.info(f"Response body: {body_text}")
                                else:
                                    self.logger.info("Response body: (streaming, no chunks)")
                            except Exception as iterator_error:
                                self.logger.warning(f"Could not iterate body_iterator: {iterator_error}")
                                self.logger.info(f"Response body: (streaming, {content_length} bytes)")
                        elif hasattr(response, '_body'):
                            # Try to access internal body attribute
                            body_content = response._body
                            if body_content:
                                body_text = body_content.decode('utf-8', errors='ignore') if isinstance(body_content, bytes) else str(body_content)
                                self.logger.info(f"Response body: {body_text}")
                            else:
                                self.logger.info(f"Response body: (streaming, {content_length} bytes)")
                        elif hasattr(response, 'render'):
                            # Try to render the response to get content
                            try:
                                import io
                                buffer = io.BytesIO()
                                response.render(buffer)
                                body_content = buffer.getvalue()
                                if body_content:
                                    body_text = body_content.decode('utf-8', errors='ignore')
                                    self.logger.info(f"Response body: {body_text}")
                                else:
                                    self.logger.info(f"Response body: (streaming, {content_length} bytes)")
                            except Exception as render_error:
                                self.logger.warning(f"Could not render response: {render_error}")
                                self.logger.info(f"Response body: (streaming, {content_length} bytes)")
                        else:
                            # Log response type for debugging
                            self.logger.info(f"Response type: {type(response)}")
                            self.logger.info(f"Response attributes: {[attr for attr in dir(response) if not attr.startswith('_')]}")
                            
                            # Try to access any available content
                            try:
                                # Check for common response content attributes
                                for attr_name in ['content', 'data', 'text', 'body']:
                                    if hasattr(response, attr_name):
                                        attr_value = getattr(response, attr_name)
                                        if attr_value:
                                            if isinstance(attr_value, bytes):
                                                content_text = attr_value.decode('utf-8', errors='ignore')
                                            else:
                                                content_text = str(attr_value)
                                            self.logger.info(f"Response body (from {attr_name}): {content_text}")
                                            break
                                else:
                                    self.logger.info(f"Response body: (streaming, {content_length} bytes)")
                            except Exception as attr_error:
                                self.logger.warning(f"Error accessing response attributes: {attr_error}")
                                self.logger.info(f"Response body: (streaming, {content_length} bytes)")
                    except Exception as stream_error:
                        self.logger.warning(f"Could not read streaming response body: {stream_error}")
                        self.logger.info(f"Response body: (streaming, {content_length} bytes)")
                else:
                    self.logger.info("Response body: (empty)")
        except Exception as e:
            self.logger.error(f"Error reading response body: {e}")
        
        self.logger.info("=== End Request Debug ===")
    
    def _wrap_streaming_response(self, response):
        """Wrap streaming response to capture and log content chunk by chunk."""
        from fastapi.responses import StreamingResponse
        import asyncio
        
        async def log_streaming_content():
            """Generator that logs each chunk as it's streamed."""
            try:
                async for chunk in response.body_iterator:
                    if chunk:
                        # Log each chunk as it comes through
                        chunk_text = chunk.decode('utf-8', errors='ignore') if isinstance(chunk, bytes) else str(chunk)
                        self.logger.info(f"Streaming chunk: {chunk_text}")
                    yield chunk
            except Exception as e:
                self.logger.error(f"Error in streaming response: {e}")
                # Re-raise to maintain error handling
                raise
        
        # Create a new streaming response with our logging generator
        return StreamingResponse(
            log_streaming_content(),
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type
        )


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

    # Auth endpoints
    @app.post("/auth/login")
    async def login(payload: Dict[str, Any]) -> Dict[str, Any]:
        """Login with username/password to get a bearer token."""
        username = payload.get("username")
        password = payload.get("password")
        if not AUTH_USERNAME or not AUTH_PASSWORD:
            return {
                "status": "error",
                "message": "Auth is not configured on server",
                "error_type": "AuthNotConfigured",
            }
        if username != AUTH_USERNAME or password != AUTH_PASSWORD:
            return {
                "status": "error",
                "message": "Invalid credentials",
                "error_type": "InvalidCredentials",
            }
        # Use configured username as subject to satisfy typing and ensure non-null value
        issued = token_store.issue_token(subject=AUTH_USERNAME, ttl_seconds=TOKEN_TTL_SECONDS)
        return {
            "status": "success",
            "message": "Login successful",
            "token": issued["token"],
            "expires_at": issued["expires_at"],
        }

    @app.post("/auth/logout")
    async def logout(request: Request) -> Dict[str, Any]:
        """Logout by revoking the provided token."""
        # Read token from header
        provided_token: Optional[str] = None
        auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            provided_token = auth_header[len("Bearer "):].strip()
        if not provided_token:
            provided_token = request.headers.get("x-mcp-token") or request.headers.get("X-MCP-Token")
        if not provided_token:
            return {
                "status": "error",
                "message": "Missing token",
                "error_type": "MissingToken",
            }
        revoked = token_store.revoke_token(provided_token)
        if not revoked and MCP_AUTH_TOKEN and provided_token == MCP_AUTH_TOKEN:
            # Fixed env token cannot be revoked via logout
            return {
                "status": "error",
                "message": "Fixed server token cannot be revoked",
                "error_type": "UnrevokableToken",
            }
        if not revoked:
            return {
                "status": "error",
                "message": "Token not found or already revoked",
                "error_type": "TokenNotFound",
            }
        return {"status": "success", "message": "Logout successful"}
    
    @app.get("/memory/get_profile_memory")
    async def rest_get_profile_memory(request: Request, limit: int = 10, memory_session_id: str = "") -> Dict[str, Any]:
        """Get the profile memory for the current session via REST endpoint.

        This endpoint reuses the shared helper to fetch profile memory using the
        resolved session id (explicit parameter takes precedence over headers).
        """
        try:
            header_user_id, header_session_id = extract_session_headers(request)
            user_id = header_user_id or DEFAULT_USER_ID
            session_id = memory_session_id or header_session_id
            return await _fetch_profile_memory(user_id=user_id, session_id=session_id, limit=limit)
        except requests.exceptions.RequestException as e:
            return create_error_response("error", f"Failed to get profile memory: {str(e)}")
        except Exception as e:
            return create_error_response("error", f"Internal error: {str(e)}")

    @app.get("/memory/get_episodic_memory")
    async def rest_get_episodic_memory(request: Request, limit: int = 10, memory_session_id: str = "") -> Dict[str, Any]:
        """Get the episodic memory for the current session via REST endpoint.

        This endpoint reuses the shared helper to fetch episodic memory using the
        resolved session id (explicit parameter takes precedence over headers).
        """
        try:
            header_user_id, header_session_id = extract_session_headers(request)
            user_id = header_user_id or DEFAULT_USER_ID
            session_id = memory_session_id or header_session_id
            return await _fetch_episodic_memory(user_id=user_id, session_id=session_id, limit=limit)
        except requests.exceptions.RequestException as e:
            return create_error_response("error", f"Failed to get episodic memory: {str(e)}")
        except Exception as e:
            return create_error_response("error", f"Internal error: {str(e)}")

    # Mirror MCP tools as REST endpoints
    @app.post("/memory/add")
    async def rest_add_memory(request: Request, content: str, memory_session_id: str) -> Dict[str, Any]:
        """REST endpoint to add a memory episode (mirrors MCP add_memory)."""
        try:
            header_user_id, header_session_id = extract_session_headers(request)
            user_id = header_user_id or DEFAULT_USER_ID
            session_id = memory_session_id or header_session_id

            result = await _handle_add_memory(user_id=user_id, session_id=session_id, content=content)
            return result
        except requests.exceptions.RequestException as e:
            return create_error_response("error", f"Failed to add memory: {str(e)}")
        except Exception as e:
            return create_error_response("error", f"Internal error: {str(e)}")

    @app.get("/memory/search")
    async def rest_search_memory(request: Request, query: str, limit: int = 5, memory_session_id: str = "") -> Dict[str, Any]:
        """REST endpoint to search memories (mirrors MCP search_memory)."""
        try:
            header_user_id, header_session_id = extract_session_headers(request)
            user_id = header_user_id or DEFAULT_USER_ID
            session_id = memory_session_id or header_session_id or DEFAULT_SESSION_ID

            return await _handle_search_memory(user_id=user_id, session_id=session_id, query=query, limit=limit)
        except requests.exceptions.RequestException as e:
            return create_error_response("error", f"Failed to search memory: {str(e)}")
        except Exception as e:
            return create_error_response("error", f"Internal error: {str(e)}")

    @app.delete("/memory/delete")
    async def rest_delete_session_memory(request: Request, memory_session_id: str) -> Dict[str, Any]:
        """REST endpoint to delete all memories for the current session (mirrors MCP delete_session_memory)."""
        try:
            header_user_id, header_session_id = extract_session_headers(request)
            user_id = header_user_id or DEFAULT_USER_ID
            session_id = memory_session_id or header_session_id
            if not session_id:
                return create_error_response("error", "Session ID is required for delete operation")
            result = await _handle_delete_session_memory(user_id=user_id, session_id=session_id)
            return result
        except requests.exceptions.RequestException as e:
            return create_error_response("error", f"Failed to delete session: {str(e)}")
        except Exception as e:
            return create_error_response("error", f"Internal error: {str(e)}")

    
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

def print_info():
    logger.info("=" * 60)
    logger.info("Printing Cursor MCP Server info")
    logger.info("=" * 60)
    logger.info(f"Port: {CURSOR_MCP_PORT}")
    logger.info(f"MemMachine Backend URL: {MEMORY_BACKEND_URL}")
    logger.info(f"Request Timeout: {REQUEST_TIMEOUT}s")
    logger.info("=" * 60)