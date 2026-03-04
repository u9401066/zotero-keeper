"""
Structured Logging Configuration

集中式結構化日誌設定，提供：
- 開發模式：人類可讀的彩色輸出
- 生產模式：JSON 格式機器可解析日誌
- MCP tool 呼叫 hook：自動記錄所有 tool 的參數、耗時、結果
- HTTP 請求日誌：記錄所有 Zotero API 存取

Environment Variables:
    LOG_LEVEL       日誌等級 (DEBUG/INFO/WARNING/ERROR, default: INFO)
    LOG_FORMAT      日誌格式 (dev/json, default: dev)
"""

import functools
import logging
import os
import time
from typing import Any

import structlog


def setup_logging(
    level: str | None = None,
    log_format: str | None = None,
) -> None:
    """
    初始化結構化日誌系統

    Args:
        level: 日誌等級 (DEBUG/INFO/WARNING/ERROR)
        log_format: 輸出格式 ("dev" = 人類可讀, "json" = 機器解析)
    """
    level = level or os.getenv("LOG_LEVEL", "INFO")
    log_format = log_format or os.getenv("LOG_FORMAT", "dev")

    log_level = getattr(logging, level.upper(), logging.INFO)

    # Shared processors for both structlog and stdlib
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if log_format == "json":
        # 生產模式：JSON 輸出
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        # 開發模式：彩色可讀輸出
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure stdlib logging to use structlog formatting
    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)

    # Quiet noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("mcp").setLevel(logging.WARNING)

    # But keep our tool hook logger at the configured level
    logging.getLogger("mcp.tool").setLevel(log_level)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """取得具名結構化 logger"""
    return structlog.get_logger(name)


# ============================================================================
# MCP Tool Hook — 自動記錄所有 tool 呼叫
# ============================================================================


def log_tool_call(func):
    """
    Decorator: 記錄 MCP tool 的呼叫參數、耗時、結果摘要

    用法:
        @mcp.tool()
        @log_tool_call
        async def search_items(query: str, limit: int = 25) -> dict:
            ...
    """
    tool_logger = structlog.get_logger("mcp.tool")

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        tool_name = func.__name__
        # 過濾掉過大的參數值（如完整 RIS 文字）
        safe_kwargs = _sanitize_params(kwargs)

        tool_logger.info(
            "tool.call",
            tool=tool_name,
            params=safe_kwargs,
        )

        start = time.perf_counter()
        try:
            result = await func(*args, **kwargs)
            elapsed = time.perf_counter() - start

            # 摘要結果（避免巨大 output 灌爆日誌）
            summary = _summarize_result(result)
            tool_logger.info(
                "tool.result",
                tool=tool_name,
                elapsed_ms=round(elapsed * 1000, 1),
                **summary,
            )
            return result

        except Exception as e:
            elapsed = time.perf_counter() - start
            tool_logger.error(
                "tool.error",
                tool=tool_name,
                elapsed_ms=round(elapsed * 1000, 1),
                error_type=type(e).__name__,
                error=str(e),
            )
            raise

    return wrapper


def _sanitize_params(params: dict[str, Any]) -> dict[str, Any]:
    """截斷過長的參數值，避免日誌過大"""
    sanitized = {}
    for k, v in params.items():
        if isinstance(v, str) and len(v) > 200:
            sanitized[k] = v[:200] + f"... ({len(v)} chars)"
        elif isinstance(v, list) and len(v) > 10:
            sanitized[k] = f"[list of {len(v)} items]"
        else:
            sanitized[k] = v
    return sanitized


def _summarize_result(result: Any) -> dict[str, Any]:
    """從 tool 結果中提取摘要資訊"""
    if not isinstance(result, dict):
        return {"result_type": type(result).__name__}

    summary: dict[str, Any] = {}

    # 常見欄位
    if "count" in result:
        summary["count"] = result["count"]
    if "error" in result:
        summary["error"] = str(result["error"])[:200]
    if "found" in result:
        summary["found"] = result["found"]
    if "success" in result:
        summary["success"] = result["success"]
    if "status" in result:
        summary["status"] = result["status"]
    if "items" in result and isinstance(result["items"], list):
        summary["items_count"] = len(result["items"])
    if "imported" in result:
        summary["imported"] = result["imported"]
    if "connected" in result:
        summary["connected"] = result["connected"]

    return summary if summary else {"result_type": "dict", "keys": list(result.keys())[:5]}
