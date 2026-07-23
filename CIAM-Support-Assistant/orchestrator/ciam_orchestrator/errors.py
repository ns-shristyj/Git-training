"""Exception hierarchy for the orchestrator.

Kept intentionally small: most failure modes should degrade to an
AgentInvocationResult with status="error"/"timeout" rather than raising, so
the orchestrator can still return a usable OrchestratorOutput (with a warning
or escalation) instead of a bare 500. These exceptions are for cases that
should hard-stop before any agent is even called.
"""


class OrchestratorError(Exception):
    """Base exception for all orchestrator-level errors."""


class ValidationError(OrchestratorError):
    """Raised on malformed/missing input before Agent 1 is ever invoked."""


class PostureViolationError(OrchestratorError):
    """Raised if the orchestrator's own code attempts an action outside
    ALLOWED_ORCHESTRATOR_ACTIONS (defense-in-depth tripwire, mirrors the
    pattern already used in Agent 1 and Agent 2)."""
