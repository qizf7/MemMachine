"""
Schemas package for the MemMachine Extension MCP Server.
"""

# Base schemas
from .base import DataT, DebugInfo, PaginatedResponseSchema, PaginationSchema, ResponseSchema

# Memory schemas
from .memory import (
    DeleteRequest,
    MemoryEpisode,
    SearchQuery,
    SessionData,
    SessionsResponseData,
)

# Auth schemas
from .auth import (
    AuthTokenData,
    LoginResponseData,
    RegistrationResponseData,
    TokenData,
    UserInfo,
    UserInfoResponseData,
    UserLogin,
    UserRegistration,
    UserResponse,
)


__all__ = [
    # Base schemas
    "DataT",
    "DebugInfo",
    "ResponseSchema",
    "PaginationSchema",
    "PaginatedResponseSchema",
    # Memory schemas
    "SessionData",
    "MemoryEpisode",
    "SearchQuery",
    "DeleteRequest",
    "SessionsResponseData",
    # Auth schemas
    "UserRegistration",
    "UserLogin",
    "UserResponse",
    "AuthTokenData",
    "TokenData",
    "UserInfo",
    "RegistrationResponseData",
    "LoginResponseData",
    "UserInfoResponseData",
]
