"""
关键词搜索路由

提供同步搜索接口，直接返回搜索结果，
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

router = APIRouter(prefix="/api/search", tags=["关键词搜索"])


class SearchRequest(BaseModel):
    """同步关键词搜索请求"""

    keyword: str = Field(..., min_length=1, description="搜索关键词")
    limit: int = Field(18, ge=1, le=200, description="返回条数上限")
    filters: Optional[Dict[str, str]] = Field(
        default=None,
        description="可选筛选条件，如 sort_type/publish_time/filter_duration",
    )
    include_raw: bool = Field(
        default=False,
        description="是否同时返回上游原始数据",
    )


class SearchResponse(BaseModel):
    """同步关键词搜索响应"""

    keyword: str
    count: int
    fields: List[str]
    filters: Dict[str, str]
    items: List[Dict[str, Any]]
    raw_count: int = 0
    raw_fields: List[str] = Field(default_factory=list)
    raw_items: Optional[List[Dict[str, Any]]] = None


@router.post("", response_model=SearchResponse)
def search_keyword(request: SearchRequest) -> Dict[str, Any]:
    """
    同步执行关键词搜索并返回结果。

    说明：
    - 直接返回当前解析后的结果列表，不需要 task_id 轮询
    - fields 为本次结果中实际出现过的字段集合，便于调用方动态适配
    - include_raw=true 时，额外返回抖音接口的原始数据
    """

    keyword = request.keyword.strip()
    if not keyword:
        raise_api_error(
            status_code=400,
            code=APIErrorCode.INVALID_REQUEST,
            message="keyword 不能为空",
            details={"field": "keyword"},
        )

    cookie = settings.get("cookie", "").strip()
    if not CookieManager.validate_cookie(cookie):
        raise_api_error(
            status_code=400,
            code=APIErrorCode.COOKIE_INVALID,
            message="Cookie 无效或已过期",
        )

    filters = request.filters or {}
    douyin = Douyin(
        target=keyword,
        limit=request.limit,
        type="search",
        down_path=settings.get("downloadPath", DOWNLOAD_DIR),
        cookie=cookie,
        user_agent=settings.get("userAgent", ""),
        filters=filters,
    )
    douyin.run()

    items = douyin.results
    fields = sorted({key for item in items for key in item.keys()})
    raw_items = douyin.raw_results if request.include_raw else None
    raw_fields = (
        sorted({key for item in raw_items for key in item.keys()}) if raw_items else []
    )

    return {
        "keyword": keyword,
        "count": len(items),
        "fields": fields,
        "filters": filters,
        "items": items,
        "raw_count": len(raw_items or []),
        "raw_fields": raw_fields,
        "raw_items": raw_items,
    }
