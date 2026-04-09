# -*- encoding: utf-8 -*-
"""HTTP bearer token authentication helpers."""

import os
import secrets

from fastapi import Request
from fastapi.responses import JSONResponse

from .api_errors import APIErrorCode, build_error_content

AUTH_ENV_VAR = "DOUYIN_API_AUTH_TOKEN"
AUTH_SCHEME = "Bearer"
MEDIA_QUERY_TOKEN_PARAM = "api_token"
PROTECTED_PATH_PREFIXES = ("/api", "/docs", "/redoc")
PROTECTED_EXACT_PATHS = {"/openapi.json"}
MEDIA_PATH_PREFIX = "/api/file/media/"


def get_api_auth_token() -> str:
    """Read the configured API token from environment variables."""
    return os.getenv(AUTH_ENV_VAR, "").strip()


def is_api_auth_enabled() -> bool:
    """Whether bearer auth is enabled for this process."""
    return bool(get_api_auth_token())


def should_protect_path(path: str) -> bool:
    """Whether the current request path should be authenticated."""
    return path in PROTECTED_EXACT_PATHS or path.startswith(PROTECTED_PATH_PREFIXES)


def parse_bearer_token(authorization: str | None) -> str | None:
    """Extract the bearer token from an Authorization header."""
    if not authorization:
        return None

    scheme, _, value = authorization.partition(" ")
    if scheme.lower() != AUTH_SCHEME.lower():
        return None

    token = value.strip()
    return token or None


def get_request_token(request: Request) -> str | None:
    """Get the request token from the supported transport."""
    header_token = parse_bearer_token(request.headers.get("Authorization"))
    if header_token:
        return header_token

    # Browsers cannot attach Authorization headers to <img>/<video> tags.
    if request.url.path.startswith(MEDIA_PATH_PREFIX):
        query_token = request.query_params.get(MEDIA_QUERY_TOKEN_PARAM, "").strip()
        if query_token:
            return query_token

    return None


def is_request_authorized(request: Request) -> bool:
    """Check whether the incoming request satisfies bearer auth."""
    expected_token = get_api_auth_token()
    if not expected_token:
        return True

    if request.method.upper() == "OPTIONS":
        return True

    if not should_protect_path(request.url.path):
        return True

    request_token = get_request_token(request)
    if not request_token:
        return False

    return secrets.compare_digest(request_token, expected_token)


def unauthorized_response() -> JSONResponse:
    """Shared 401 response for auth failures."""
    return JSONResponse(
        status_code=401,
        content=build_error_content(
            code=APIErrorCode.UNAUTHORIZED,
            message="缺少或无效的 API Token",
        ),
        headers={"WWW-Authenticate": AUTH_SCHEME},
    )
