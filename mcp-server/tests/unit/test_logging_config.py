"""
Tests for structured logging configuration
"""

import asyncio
import logging

import pytest

from zotero_mcp.infrastructure.logging_config import (
    get_logger,
    log_tool_call,
    setup_logging,
    _sanitize_params,
    _summarize_result,
)


class TestSetupLogging:
    """Test logging initialization"""

    def test_setup_logging_default(self):
        """Should initialize with default settings (INFO, dev format)"""
        setup_logging()
        root = logging.getLogger()
        assert root.level == logging.INFO
        assert len(root.handlers) == 1

    def test_setup_logging_debug_level(self):
        """Should respect LOG_LEVEL setting"""
        setup_logging(level="DEBUG")
        root = logging.getLogger()
        assert root.level == logging.DEBUG

    def test_setup_logging_json_format(self):
        """Should accept json format without error"""
        setup_logging(log_format="json")
        root = logging.getLogger()
        assert len(root.handlers) == 1

    def test_get_logger_returns_bound_logger(self):
        """Should return a structlog BoundLogger"""
        setup_logging()
        logger = get_logger("test.module")
        assert logger is not None

    def test_mcp_tool_logger_not_silenced(self):
        """mcp.tool logger should be at configured level, not WARNING"""
        setup_logging(level="INFO")
        tool_logger = logging.getLogger("mcp.tool")
        assert tool_logger.level == logging.INFO

    def test_httpx_logger_silenced(self):
        """httpx logger should be at WARNING to reduce noise"""
        setup_logging()
        assert logging.getLogger("httpx").level == logging.WARNING


class TestLogToolCall:
    """Test the MCP tool call hook decorator"""

    def test_decorates_async_function(self):
        """Should preserve function name and signature"""

        @log_tool_call
        async def my_tool(query: str, limit: int = 10) -> dict:
            """My tool docstring"""
            return {"count": 0}

        assert my_tool.__name__ == "my_tool"

    def test_logs_successful_call(self):
        """Should return result unchanged"""

        @log_tool_call
        async def search(query: str) -> dict:
            return {"count": 5, "items": [1, 2, 3, 4, 5]}

        result = asyncio.get_event_loop().run_until_complete(search(query="test"))
        assert result["count"] == 5
        assert len(result["items"]) == 5

    def test_logs_error_and_reraises(self):
        """Should re-raise exception after logging"""

        @log_tool_call
        async def bad_tool() -> dict:
            raise ValueError("broken")

        with pytest.raises(ValueError, match="broken"):
            asyncio.get_event_loop().run_until_complete(bad_tool())


class TestSanitizeParams:
    """Test parameter sanitization"""

    def test_short_strings_pass_through(self):
        assert _sanitize_params({"q": "test"}) == {"q": "test"}

    def test_long_strings_truncated(self):
        long_str = "x" * 500
        result = _sanitize_params({"ris": long_str})
        assert "500 chars" in result["ris"]
        assert len(result["ris"]) < 250

    def test_long_lists_summarized(self):
        result = _sanitize_params({"pmids": list(range(50))})
        assert result["pmids"] == "[list of 50 items]"

    def test_numbers_pass_through(self):
        assert _sanitize_params({"limit": 25}) == {"limit": 25}


class TestSummarizeResult:
    """Test result summarization"""

    def test_count_field(self):
        assert _summarize_result({"count": 10})["count"] == 10

    def test_items_list(self):
        result = _summarize_result({"items": [1, 2, 3]})
        assert result["items_count"] == 3

    def test_error_field(self):
        result = _summarize_result({"error": "connection failed"})
        assert "connection failed" in result["error"]

    def test_success_field(self):
        result = _summarize_result({"success": True})
        assert result["success"] is True

    def test_non_dict_result(self):
        result = _summarize_result("plain string")
        assert result["result_type"] == "str"

    def test_unknown_dict_shows_keys(self):
        result = _summarize_result({"foo": 1, "bar": 2})
        assert "keys" in result
