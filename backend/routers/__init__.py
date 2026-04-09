"""
路由模块

包含所有 FastAPI 路由定义。
"""

from .aweme import router as aweme_router
from .aria2 import router as aria2_router
from .file import router as file_router
from .search import router as search_router
from .settings import router as settings_router
from .system import router as system_router
from .task import router as task_router

__all__ = [
    "aweme_router",
    "task_router",
    "search_router",
    "settings_router",
    "aria2_router",
    "file_router",
    "system_router",
]
