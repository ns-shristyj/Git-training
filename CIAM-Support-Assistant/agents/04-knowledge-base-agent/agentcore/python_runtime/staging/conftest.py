"""Provides a minimal stub for `bedrock_agentcore` so agent.py can be
imported and unit-tested without the real AgentCore SDK installed (the real
SDK is only bundled into the deployment zip for actual AWS runtime use --
the pip-published `bedrock-agentcore` package is a 0.0.1 placeholder with no
usable exports, so tests can't rely on it locally).
"""

import sys
import types

import pytest


def _install_stub():
    if "bedrock_agentcore" in sys.modules:
        return

    module = types.ModuleType("bedrock_agentcore")

    class BedrockAgentCoreApp:
        def entrypoint(self, func):
            return func

        def run(self):
            pass

    module.BedrockAgentCoreApp = BedrockAgentCoreApp
    sys.modules["bedrock_agentcore"] = module


_install_stub()


@pytest.fixture(autouse=True)
def _no_live_auth0_fetch(monkeypatch):
    """Tool 5 (fetch_live_auth0_actions) makes real Secrets Manager +
    Auth0 Management API calls -- never allow that during unit tests (it
    was silently doing so before this fixture existed, adding real network
    latency and flakiness to the suite). Default: simulate a fetch that
    found nothing live (empty dict, no error), so Tool 4 falls back to its
    offline snapshot -- identical to Tool 4's behavior before Tool 5
    existed, so this doesn't change any existing test's expectations.
    Tests that specifically exercise live-fetch/drift-detection behavior
    override this again with their own monkeypatch."""
    import agent
    monkeypatch.setattr(agent, "fetch_live_auth0_actions", lambda names: ({}, None))
