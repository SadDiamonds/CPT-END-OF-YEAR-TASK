"""Utility helpers for awarding shared currencies across systems."""

from __future__ import annotations

from typing import Any, MutableMapping

from config import AUTOMATION_REWARD_RATIO

GameState = MutableMapping[str, Any]


def _normalize_amount(value: Any) -> int:
    """Convert arbitrary numeric input into a non-negative integer."""
    try:
        return max(0, int(round(float(value))))
    except Exception:
        return 0


def grant_stability_currency(game_state: GameState, amount: Any) -> int:
    """Deposit collapse rewards into the shared stability pool."""
    delta = _normalize_amount(amount)
    if delta <= 0:
        return 0
    current = _normalize_amount(game_state.get("stability_currency", 0))
    game_state["stability_currency"] = current + delta
    return delta


def grant_automation_currency(
    game_state: GameState,
    collapse_reward: Any,
    ratio: float = AUTOMATION_REWARD_RATIO,
) -> int:
    """Convert a collapse reward into automation fuel according to the configured ratio."""
    base = _normalize_amount(collapse_reward)
    if base <= 0 or ratio <= 0:
        return 0
    delta = _normalize_amount(base * float(ratio))
    if delta <= 0:
        return 0
    current = _normalize_amount(game_state.get("automation_currency", 0))
    game_state["automation_currency"] = current + delta
    return delta
