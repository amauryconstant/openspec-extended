#!/usr/bin/env python3
"""PHASE0 auto-fix dispatch tests.

The engine's PHASE0 self-healing loop reads ``routes_pending`` after each
``run_agent`` invocation. When every pending route is in
``AUTO_FIXABLE_ROUTES``, the engine clears ``routes_pending``, invokes the
registered auto-fix agent via ``_run_auto_fix``, and re-enters the phase to
verify. Mixed routes (auto-fixable + user-judgment-required) keep the
halt-and-surface behavior; non-auto-fixable routes alone also halt.

These tests cover the membership helper, the dispatch lookup, and the
engine's branching — without spawning any AI subprocess.
"""

from __future__ import annotations

import pytest

from source.orchestrator.engine import (
    AUTO_FIX_AGENTS,
    AUTO_FIXABLE_ROUTES,
    _auto_fix_agent_for,
    _is_auto_fixable_route,
)


@pytest.mark.unit
class TestAutoFixableRouteMembership:
    """`_is_auto_fixable_route` accepts both `/route` and `route` forms."""

    @pytest.mark.parametrize(
        "route",
        [
            "/osc-update-change",
            "osc-update-change",
        ],
    )
    def test_osc_update_change_is_auto_fixable(self, route: str) -> None:
        assert _is_auto_fixable_route(route) is True

    @pytest.mark.parametrize(
        "route",
        [
            "/osc-continue-change",
            "/osc-new-change",
            "/osc-archive-change",
            "/osc-explore",
            "/osc-bulk-archive-change",
            "/osc-apply-change",
            "/osc-sync-specs",
            "/osc-verify-change",
            "totally-unrelated",
        ],
    )
    def test_other_routes_are_not_auto_fixable(self, route: str) -> None:
        assert _is_auto_fixable_route(route) is False

    def test_empty_string_is_not_auto_fixable(self) -> None:
        assert _is_auto_fixable_route("") is False


@pytest.mark.unit
class TestAutoFixAgentLookup:
    """`_auto_fix_agent_for` returns the registered agent or empty string."""

    def test_osc_update_change_resolves_to_osx_editor(self) -> None:
        assert _auto_fix_agent_for("osc-update-change") == "osx-editor"
        assert _auto_fix_agent_for("/osc-update-change") == "osx-editor"

    def test_unknown_route_returns_empty_string(self) -> None:
        assert _auto_fix_agent_for("/osc-continue-change") == ""
        assert _auto_fix_agent_for("") == ""


@pytest.mark.unit
class TestAutoFixableRoutesConstant:
    """`AUTO_FIXABLE_ROUTES` is a frozen set with exactly the expected entries."""

    def test_set_is_frozen(self) -> None:
        with pytest.raises(AttributeError):
            AUTO_FIXABLE_ROUTES.add("osc-continue-change")  # type: ignore[attr-defined]

    def test_set_contains_only_osc_update_change(self) -> None:
        assert AUTO_FIXABLE_ROUTES == frozenset({"osc-update-change"})

    def test_agent_registry_matches_routes(self) -> None:
        """Every auto-fixable route has a registered agent. Catches drift."""
        for route in AUTO_FIXABLE_ROUTES:
            assert route in AUTO_FIX_AGENTS, (
                f"route {route!r} is in AUTO_FIXABLE_ROUTES but has no "
                f"agent registered in AUTO_FIX_AGENTS — engine dispatch "
                f"would log an error and halt on this route."
            )
            assert AUTO_FIX_AGENTS[route], (
                f"agent registered for route {route!r} is empty"
            )
