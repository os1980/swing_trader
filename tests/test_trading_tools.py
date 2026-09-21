"""Tool construction in src/tools/trading_tools.py.

Needs crewai and the data-provider packages, which CI does not install, so the module
is skipped there and runs locally after `make setup`.
"""
from __future__ import annotations

import pytest

pytest.importorskip("crewai")
pytest.importorskip("finnhub")
pytest.importorskip("langchain_tavily")

from src.tools.trading_tools import TOOL_NAMES, build_tools  # noqa: E402


def _run_one_crew(tool_obj) -> str:
    """Mirror what CrewAI 1.8.1 does with a tool during one crew run.

    The agent converts the tool with to_structured_tool(), which copies the current usage
    count, checks the limit, and on use writes the incremented count back to the original.
    """
    structured = tool_obj.to_structured_tool()
    if structured.has_reached_max_usage_count():
        return "locked"
    structured._increment_usage_count()
    return "used"


def test_shared_tool_object_locks_after_the_first_crew():
    """Documents the old defect, so the regression test below means something."""
    (shared,) = build_tools("get_macroeconomic_news")
    assert [_run_one_crew(shared) for _ in range(3)] == ["used", "locked", "locked"]


def test_fresh_tools_per_crew_never_lock():
    outcomes = [_run_one_crew(build_tools("get_macroeconomic_news")[0]) for _ in range(3)]
    assert outcomes == ["used", "used", "used"]


def test_build_tools_returns_new_objects_each_time():
    first = build_tools(*TOOL_NAMES)
    second = build_tools(*TOOL_NAMES)
    assert [t.name for t in first] == list(TOOL_NAMES)
    assert all(a is not b for a, b in zip(first, second, strict=True))
    assert all(t.max_usage_count == 1 and t.current_usage_count == 0 for t in first)


def test_unknown_tool_name_fails_loudly():
    with pytest.raises(KeyError, match="get_nonexistent"):
        build_tools("get_nonexistent")
