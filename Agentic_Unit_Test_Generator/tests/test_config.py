"""Unit tests for CIAM-Support-Assistant.orchestrator.ciam_orchestrator.config."""

import pytest

from CIAM_Support_Assistant.orchestrator.ciam_orchestrator import config as cfg


class TestAgent2InputBuilder:
    def test_typical_and_missing_fields(self):
        """Builds email/run_id payload for a full envelope and defaults run_id to '' when absent."""
        full = {"extracted_email": "user@example.com", "run_id": "abc-123"}
        assert cfg._agent2_input_builder(full) == {
            "email": "user@example.com",
            "run_id": "abc-123",
        }

        empty = {}
        assert cfg._agent2_input_builder(empty) == {"email": None, "run_id": ""}

    @pytest.mark.parametrize("bad_input", [None, "not a dict", 42, ["a", "list"]])
    def test_non_dict_input_raises_attribute_error(self, bad_input):
        """Non-dict envelopes lack .get and raise AttributeError instead of being silently accepted."""
        with pytest.raises(AttributeError):
            cfg._agent2_input_builder(bad_input)


class TestAgent3InputBuilder:
    def test_typical_and_missing_fields(self):
        """Extracts email from the envelope, returning None when the key is absent."""
        full = {"extracted_email": "user@example.com"}
        assert cfg._agent3_input_builder(full) == {"email": "user@example.com"}

        empty = {}
        assert cfg._agent3_input_builder(empty) == {"email": None}

    @pytest.mark.parametrize("bad_input", [None, 3.14, ("tuple",)])
    def test_non_dict_input_raises_attribute_error(self, bad_input):
        """Non-dict envelopes cannot call .get and raise AttributeError."""
        with pytest.raises(AttributeError):
            cfg._agent3_input_builder(bad_input)


class TestAgent4InputBuilder:
    def test_typical_and_missing_fields(self):
        """Extracts intent/portal_hint from the envelope, defaulting to None when absent."""
        full = {"intent": "password_reset", "portal_hint": "b2c"}
        assert cfg._agent4_input_builder(full) == {
            "intent": "password_reset",
            "portal_hint": "b2c",
        }

        empty = {}
        assert cfg._agent4_input_builder(empty) == {"intent": None, "portal_hint": None}

    @pytest.mark.parametrize("bad_input", [None, 7, True])
    def test_non_dict_input_raises_attribute_error(self, bad_input):
        """Non-dict envelopes cannot call .get and raise AttributeError."""
        with pytest.raises(AttributeError):
            cfg._agent4_input_builder(bad_input)


class TestAgentRegistryStructure:
    def test_registry_entries_are_well_formed(self):
        """AGENT_REGISTRY exposes agent_2/3/4 with required keys and callable input_builders."""
        expected_keys = {"name", "arn", "enabled", "routing_flag", "input_builder", "output_key"}
        assert set(cfg.AGENT_REGISTRY.keys()) == {"agent_2", "agent_3", "agent_4"}

        for agent_key, entry in cfg.AGENT_REGISTRY.items():
            assert expected_keys.issubset(entry.keys())
            assert isinstance(entry["name"], str) and entry["name"]
            assert isinstance(entry["enabled"], bool)
            assert isinstance(entry["routing_flag"], str) and entry["routing_flag"]
            assert callable(entry["input_builder"])
            assert isinstance(entry["output_key"], str) and entry["output_key"]

    def test_agent2_enabled_by_default_others_disabled(self):
        """Reflects the staged-rollout posture: agent_2 defaults enabled, agent_3/4 default disabled."""
        assert cfg.AGENT_REGISTRY["agent_2"]["enabled"] is True
        assert cfg.AGENT_REGISTRY["agent_3"]["enabled"] is False
        assert cfg.AGENT_REGISTRY["agent_4"]["enabled"] is False


class TestModuleLevelConfigValues:
    def test_config_constants_have_expected_types_and_safe_defaults(self):
        """Numeric/collection config values parse to correct types and posture guard restricts to one action."""
        assert isinstance(cfg.CONFIDENCE_THRESHOLD, float)
        assert isinstance(cfg.AGENT_TIMEOUT_SECONDS, int)
        assert cfg.ALLOWED_ORCHESTRATOR_ACTIONS == frozenset(
            {"bedrock-agentcore:InvokeAgentRuntime"}
        )
        assert isinstance(cfg.ALLOWED_ORCHESTRATOR_ACTIONS, frozenset)
