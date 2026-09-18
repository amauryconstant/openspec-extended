import pytest

from source.lib import osx
from source.orchestrator import engine


pytestmark = pytest.mark.unit


def test_phase_constants_share_library_identity():
    assert id(osx.PHASES) == id(engine.PHASES)
    assert id(osx.PHASE_NAMES) == id(engine.PHASE_NAMES)
    assert id(osx.PHASE_COMMANDS) == id(engine.PHASE_COMMANDS)


def test_phase_transition_shares_library_identity():
    """The engine must not keep its own copy of the transition table."""
    assert engine.advance_phase is osx.get_next_phase
