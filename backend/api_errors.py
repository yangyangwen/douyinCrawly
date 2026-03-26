# -*- encoding: utf-8 -*-
"""
HTTP API 错误模型与异常处理。

为 FastAPI 路由提供统一的错误结构，避免不同接口返回风格不一致。
"""

from enum import Enum
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from loguru import logger
from pydantic import BaseModel

ErrorDetails = Dict[str, Any] | List[Dict[str, Any]]


class APIErrorCode(str, Enum):
    """统一错误码。"""

    INVALID_REQUEST = "INVALID_REQUEST"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    CONFIG_INVALID = "CONFIG_INVALID"
    COOKIE_INVALID = "COOKIE_INVALID"
    TASK_NOT_FOUND = "TASK_NOT_FOUND"
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class APIErrorPayload(BaseModel):
    """错误详情。"""

    code: str
    message: str
    details: ErrorDetails | None = None


class ErrorResponse(BaseModel):
    """统一错误响应。"""

    error: APIErrorPayload


class APIError(Exception):
    """应用级 API 异常。"""

    def __init__(
        self,
        status_code: int,
        code: APIErrorCode | str,
        message: str,
        details: ErrorDetails | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = _serialize_code(code)
        self.message = message
        self.details = details


def raise_api_error(
    status_code: int,
    code: APIErrorCode | str,
    message: str,
    details: ErrorDetails | None = None,
) -> None:
    """抛出统一结构的 APIError。"""
    raise APIError(status_code=status_code, code=code, message=message, details=details)


def _build_error_content(
    code: APIErrorCode | str,
    message: str,
    details: ErrorDetails | None = None,
) -> Dict[str, Any]:
    content: Dict[str, Any] = {
        "error": {
            "code": _serialize_code(code),
            "message": message,
        }
    }
    if details is not None:
        content["error"]["details"] = details
    return content


def _serialize_code(code: APIErrorCode | str) -> str:
    if isinstance(code, APIErrorCode):
        return code.value
    return str(code)


def _default_error_code(status_code: int) -> APIErrorCode:
    if status_code == 422:
        return APIErrorCode.VALIDATION_ERROR
    if status_code == 404:
        return APIErrorCode.RESOURCE_NOT_FOUND
    if status_code == 503:
        return APIErrorCode.SERVICE_UNAVAILABLE
    if status_code >= 500:
        return APIErrorCode.INTERNAL_ERROR
    return APIErrorCode.INVALID_REQUEST


def _normalize_http_exception(exc: HTTPException) -> APIError:
    status_code = exc.status_code
    default_code = _default_error_code(status_code)
    detail = exc.detail

    if isinstance(detail, dict):
        error_obj = detail.get("error") if isinstance(detail.get("error"), dict) else detail
        code = error_obj.get("code", default_code)
        message = error_obj.get("message") or error_obj.get("detail") or str(detail)
        details = error_obj.get("details")
        return APIError(
            status_code=status_code,
            code=code,
            message=message,
            details=details,
        )

    if isinstance(detail, str):
        return APIError(status_code=status_code, code=default_code, message=detail)

    return APIError(
        status_code=status_code,
        code=default_code,
        message="请求失败",
        details={"detail": detail},
    )


def _format_validation_errors(exc: RequestValidationError) -> List[Dict[str, str]]:
    errors: List[Dict[str, str]] = []
    for item in exc.errors():
        field = ".".join(str(part) for part in item.get("loc", []))
        errors.append(
            {
                "field": field,
                "message": item.get("msg", "参数校验失败"),
                "type": item.get("type", "validation_error"),
            }
        )
    return errors


async def api_error_exception_handler(
    _request: Request,
    exc: APIError,
) -> JSONResponse:
    """APIError 统一输出。"""
    return JSONResponse(
        status_code=exc.status_code,
        content=_build_error_content(
            code=exc.code,
            message=exc.message,
            details=exc.details,
        ),
    )


async def http_exception_handler(
    request: Request,
    exc: HTTPException,
) -> JSONResponse:
    """兜底处理仍然抛出 HTTPException 的路由。"""
    return await api_error_exception_handler(request, _normalize_http_exception(exc))


async def validation_exception_handler(
    _request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """请求参数校验错误。"""
    return JSONResponse(
        status_code=422,
        content=_build_error_content(
            code=APIErrorCode.VALIDATION_ERROR,
            message="请求参数校验失败",
            details=_format_validation_errors(exc),
        ),
    )


async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """未处理异常统一转成稳定错误结构。"""
    logger.exception(f"未处理异常: {request.method} {request.url.path} - {exc}")
    return JSONResponse(
        status_code=500,
        content=_build_error_content(
            code=APIErrorCode.INTERNAL_ERROR,
            message="服务器内部错误",
        ),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """注册统一异常处理。"""
    app.add_exception_handler(APIError, api_error_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
