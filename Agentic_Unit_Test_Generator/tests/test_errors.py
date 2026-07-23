"""Unit tests for ciam_orchestrator.errors exception hierarchy."""

import pytest

from CIAM_Support_Assistant.orchestrator.ciam_orchestrator.errors import (
    OrchestratorError,
    ValidationError,
    PostureViolationError,
)


class TestExceptionHierarchy:
    """Tests validating core behavior of the exception hierarchy."""

    @pytest.mark.parametrize(
        "exc_class",
        [OrchestratorError, ValidationError, PostureViolationError],
    )
    def test_is_exception_subclass(self, exc_class):
        """Each defined error class must be a subclass of Exception."""
        assert issubclass(exc_class, Exception)

    @pytest.mark.parametrize(
        "exc_class",
        [ValidationError, PostureViolationError],
    )
    def test_subclasses_derive_from_orchestrator_error(self, exc_class):
        """ValidationError and PostureViolationError must derive from OrchestratorError."""
        assert issubclass(exc_class, OrchestratorError)

    @pytest.mark.parametrize(
        "exc_class,message",
        [
            (OrchestratorError, "generic failure"),
            (ValidationError, "missing required field"),
            (PostureViolationError, "action outside allowed set"),
        ],
    )
    def test_raise_and_capture_message(self, exc_class, message):
        """Raising each exception type preserves the provided message and is catchable by its own type."""
        with pytest.raises(exc_class) as exc_info:
            raise exc_class(message)
        assert str(exc_info.value) == message

    def test_subclass_caught_by_base_class(self):
        """ValidationError and PostureViolationError can be caught via the base OrchestratorError type."""
        with pytest.raises(OrchestratorError):
            raise ValidationError("bad input")

        with pytest.raises(OrchestratorError):
            raise PostureViolationError("posture tripwire")


class TestExceptionEdgeCases:
    """Tests validating edge-case instantiation of exception classes."""

    @pytest.mark.parametrize(
        "exc_class",
        [OrchestratorError, ValidationError, PostureViolationError],
    )
    def test_instantiate_with_no_arguments(self, exc_class):
        """Each exception can be instantiated with no message argument and stringifies to empty string."""
        instance = exc_class()
        assert isinstance(instance, exc_class)
        assert str(instance) == ""

    @pytest.mark.parametrize(
        "exc_class",
        [OrchestratorError, ValidationError, PostureViolationError],
    )
    def test_instantiate_with_multiple_positional_arguments(self, exc_class):
        """Each exception supports multiple positional args like the base Exception class."""
        instance = exc_class("part1", "part2", 42)
        assert instance.args == ("part1", "part2", 42)

    @pytest.mark.parametrize(
        "exc_class",
        [OrchestratorError, ValidationError, PostureViolationError],
    )
    def test_instantiate_with_non_string_argument(self, exc_class):
        """Each exception accepts a non-string argument (e.g. a dict) without raising during construction."""
        payload = {"field": "value"}
        instance = exc_class(payload)
        assert instance.args == (payload,)
