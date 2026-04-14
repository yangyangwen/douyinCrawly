"""
单个作品详情路由

提供同步详情接口，直接返回单个作品解析结果，
适合外部系统按 HTTP 方式调用。
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ..api_errors import APIErrorCode, raise_api_error
from ..constants import DOWNLOAD_DIR
from ..lib.cookies import CookieManager
from ..lib.douyin import Douyin
from ..settings import settings

router = APIRouter(prefix="/api/aweme", tags=["单作品详情"])


class AwemeDetailRequest(BaseModel):
    """同步单作品详情请求"""

    target: str = Field(..., min_length=1, description="作品URL或aweme_id")
    include_raw: bool = Field(
        default=False,
        description="是否同时返回上游原始数据",
    )


class AwemeMetrics(BaseModel):
    """标准化互动指标"""

    liked_count: int
    comment_count: int
    collect_count: int
    share_count: int


class AwemeDetailResponse(BaseModel):
    """同步单作品详情响应"""

    target: str
    aweme_id: str
    resolved_url: str
    content_type: str
    fields: List[str]
    metrics: AwemeMetrics
    item: Dict[str, Any]
    raw_fields: List[str] = Field(default_factory=list)
    raw_item: Optional[Dict[str, Any]] = None


class AwemeFeedMetricsResponse(BaseModel):
    """Feed 互动数据响应"""

    success: bool = True
    data: AwemeMetrics
    message: str = "获取Feed互动数据成功"


def _build_aweme_detail_payload(request: AwemeDetailRequest) -> Dict[str, Any]:
    """
    同步执行单作品详情抓取并返回结果。

    说明：
    - 支持传入抖音作品 URL 或纯 aweme_id
    - 直接返回当前解析后的详情结果，不需要 task_id 轮询
    - include_raw=true 时，额外返回抖音接口的原始详情数据
    """

    target = request.target.strip()
    if not target:
        raise_api_error(
            status_code=400,
            code=APIErrorCode.INVALID_REQUEST,
            message="target 不能为空",
            details={"field": "target"},
        )

    cookie = settings.get("cookie", "").strip()
    if not CookieManager.validate_cookie(cookie):
        raise_api_error(
            status_code=400,
            code=APIErrorCode.COOKIE_INVALID,
            message="Cookie 无效或已过期",
        )

    douyin = Douyin(
        target=target,
        limit=1,
        type="aweme",
        down_path=settings.get("downloadPath", DOWNLOAD_DIR),
        cookie=cookie,
        user_agent=settings.get("userAgent", ""),
    )

    try:
        douyin.run()
    except Exception as exc:
        message = str(exc)
        if "目标输入错误" in message:
            raise_api_error(
                status_code=400,
                code=APIErrorCode.INVALID_REQUEST,
                message=message,
                details={"field": "target"},
            )
        if "cookie无效" in message.lower() or "cookie" in message.lower():
            raise_api_error(
                status_code=400,
                code=APIErrorCode.COOKIE_INVALID,
                message="Cookie 无效或已过期",
            )
        if "作品详情获取失败" in message:
            raise_api_error(
                status_code=404,
                code=APIErrorCode.RESOURCE_NOT_FOUND,
                message="作品不存在或详情获取失败",
                details={"target": target},
            )
        raise

    if not douyin.results:
        raise_api_error(
            status_code=404,
            code=APIErrorCode.RESOURCE_NOT_FOUND,
            message="作品不存在或详情获取失败",
            details={"target": target},
        )

    item = douyin.results[0]
    aweme_id = str(item.get("id", douyin.id or ""))
    content_type = "image" if item.get("type") == 68 else "video"
    if target.startswith(("http://", "https://")):
        resolved_url = target
    else:
        path_type = "note" if content_type == "image" else "video"
        resolved_url = f"https://www.douyin.com/{path_type}/{aweme_id}"
    raw_item = douyin.raw_results[0] if request.include_raw and douyin.raw_results else None

    return {
        "target": target,
        "aweme_id": aweme_id,
        "resolved_url": resolved_url,
        "content_type": content_type,
        "fields": sorted(item.keys()),
        "metrics": {
            "liked_count": int(item.get("digg_count", 0) or 0),
            "comment_count": int(item.get("comment_count", 0) or 0),
            "collect_count": int(item.get("collect_count", 0) or 0),
            "share_count": int(item.get("share_count", 0) or 0),
        },
        "item": item,
        "raw_fields": sorted(raw_item.keys()) if raw_item else [],
        "raw_item": raw_item,
    }


@router.post("/detail", response_model=AwemeDetailResponse)
def get_aweme_detail(request: AwemeDetailRequest) -> Dict[str, Any]:
    return _build_aweme_detail_payload(request)


@router.post("/detail/feed-metrics", response_model=AwemeFeedMetricsResponse)
def get_aweme_feed_metrics(request: AwemeDetailRequest) -> Dict[str, Any]:
    detail = _build_aweme_detail_payload(request)
    return {
        "success": True,
        "data": detail["metrics"],
        "message": "获取Feed互动数据成功",
    }
