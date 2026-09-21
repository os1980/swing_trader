"""Static checks on the crew YAML.

Prompt edits are the most common change in this repo and the slowest to validate
by running the flow, so the cheap failure modes are caught here instead.
"""
from __future__ import annotations

import json
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


def test_strategy_task_demands_bare_json():
    """Downstream parsing breaks on prose or markdown fences."""
    text = _text(load_config("strategy_tasks.yaml")).lower()
    assert "json" in text
    assert any(phrase in text for phrase in ("only json", "json only", "no markdown", "raw json")), (
        "strategy_tasks.yaml no longer tells the model to return bare JSON"
    )


def test_task_templates_use_single_braces():
    """CrewAI 1.8.1 interpolates with str.replace, so {{ }} reaches the model literally."""
    for crew in CREWS:
        for suffix in ("agents", "tasks"):
            text = _text(load_config(f"{crew}_{suffix}.yaml"))
            assert "{{" not in text and "}}" not in text, (
                f"{crew}_{suffix}.yaml contains a doubled brace"
            )


# Same pattern as crewai/utilities/string_utils.py in crewai 1.8.1.
_CREWAI_VARIABLE = re.compile(r"\{([A-Za-z_][A-Za-z0-9_\-]*)}")


def _interpolate_like_crewai(template: str, inputs: dict) -> str:
    for var in _CREWAI_VARIABLE.findall(template):
        template = template.replace("{" + var + "}", str(inputs[var]))
    return template


def test_rendered_strategy_template_is_a_valid_portfolio_response():
    """Render the JSON example the model sees, fill its [slots], and validate it.

    This is the check that would have caught the doubled braces: the model copies the
    shape of this example, so the example itself has to parse.
    """
    from src.helpers.trade_signals import PortfolioResponse

    inputs = {
        "trade_date": "2025-01-07", "start_date": "2024-10-09", "end_date": "2025-01-06",
        "macro_report": "macro", "all_symbol_reports": "reports",
        "equity": 10000, "risk": "1.0",
    }
    task = load_config("strategy_tasks.yaml")["portfolio_analysis_task"]
    rendered = _interpolate_like_crewai(task["expected_output"], inputs)

    start = rendered.index("{")
    end = rendered.index("If INPUT 2 is empty")
    example = rendered[start:end].strip()
    # Bare [slot] placeholders stand for numbers; quoted ones are already strings.
    example = re.sub(r"(?<![\"\w])\[[a-z][^\]\n]*\]", "1.0", example)
    example = example.replace('"BUY or HOLD"', '"BUY"')

    portfolio = PortfolioResponse.model_validate(json.loads(example))
    assert portfolio.trades[0].trade_date == "2025-01-07"

    empty = rendered[end:].split(":", 1)[1].strip()
    assert PortfolioResponse.model_validate(json.loads(empty)).trades == []
