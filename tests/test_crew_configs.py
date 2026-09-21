"""Static checks on the crew YAML.

Prompt edits are the most common change in this repo and the slowest to validate
by running the flow, so the cheap failure modes are caught here instead.
"""
from __future__ import annotations

import re

import pytest

from .conftest import CREW_INPUTS, load_config

CREWS = ["macro", "analysis", "strategy"]
PLACEHOLDER = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


def _text(config: dict) -> str:
    """Every string value in a parsed config, joined. Comments are already dropped."""
    parts: list[str] = []
    for entry in config.values():
        for value in entry.values():
            if isinstance(value, str):
                parts.append(value)
    return "\n".join(parts)


@pytest.mark.parametrize("crew", CREWS)
def test_agent_config_has_required_keys(crew):
    agents = load_config(f"{crew}_agents.yaml")
    assert agents, f"{crew}_agents.yaml is empty"
    for name, entry in agents.items():
        for key in ("role", "goal", "backstory"):
            assert entry.get(key), f"{crew} agent {name} is missing {key}"


@pytest.mark.parametrize("crew", CREWS)
def test_task_config_has_required_keys(crew):
    tasks = load_config(f"{crew}_tasks.yaml")
    agents = load_config(f"{crew}_agents.yaml")
    assert tasks, f"{crew}_tasks.yaml is empty"
    for name, entry in tasks.items():
        for key in ("description", "expected_output", "agent"):
            assert entry.get(key), f"{crew} task {name} is missing {key}"
        assert entry["agent"] in agents, (
            f"{crew} task {name} names agent {entry['agent']!r}, which is not in "
            f"{crew}_agents.yaml"
        )


@pytest.mark.parametrize("crew", CREWS)
def test_placeholders_are_supplied_at_kickoff(crew):
    """Catch a {typo} before it costs an LLM run."""
    allowed = CREW_INPUTS[crew]
    for suffix in ("agents", "tasks"):
        config = load_config(f"{crew}_{suffix}.yaml")
        used = set(PLACEHOLDER.findall(_text(config)))
        unknown = used - allowed
        assert not unknown, (
            f"{crew}_{suffix}.yaml uses {sorted(unknown)}, which src/main.py does not pass "
            f"to the {crew} crew. Supplied inputs: {sorted(allowed)}"
        )


@pytest.mark.parametrize(
    "crew",
    [
        "macro",
        "analysis",
        pytest.param(
            "strategy",
            marks=pytest.mark.xfail(
                reason="The active strategy prompts dropped every end_date mention; only the "
                       "commented-out per-symbol block still carries the bound.",
                strict=False,
            ),
        ),
    ],
)
def test_prompts_keep_the_no_lookahead_bound(crew):
    """Every crew must bind its data window to end_date, not to the trade date."""
    text = "\n".join(
        _text(load_config(f"{crew}_{suffix}.yaml")) for suffix in ("agents", "tasks")
    )
    assert "end_date" in text, (
        f"the {crew} crew prompts no longer mention end_date; the no-lookahead bound is gone"
    )


@pytest.mark.xfail(
    reason="Known defect from code review: the 'return only valid JSON, no markdown' rule "
           "was deleted from the strategy task.",
    strict=False,
)
def test_strategy_task_demands_bare_json():
    """Downstream parsing breaks on prose or markdown fences."""
    text = _text(load_config("strategy_tasks.yaml")).lower()
    assert "json" in text
    assert any(phrase in text for phrase in ("only json", "json only", "no markdown", "raw json")), (
        "strategy_tasks.yaml no longer tells the model to return bare JSON"
    )


@pytest.mark.xfail(
    reason="Known defect from code review: CrewAI 1.8.1 interpolates with str.replace, "
           "so {{ }} is not unescaped and reaches the model literally.",
    strict=False,
)
def test_task_templates_use_single_braces():
    for crew in CREWS:
        text = _text(load_config(f"{crew}_tasks.yaml"))
        assert "{{" not in text, f"{crew}_tasks.yaml contains a doubled brace"
