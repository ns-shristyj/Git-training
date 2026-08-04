"""Provides a minimal stub for `bedrock_agentcore` so agent.py can be
imported and unit-tested without the real AgentCore SDK installed (the real
SDK is only bundled into the deployment zip for actual AWS runtime use --
the pip-published `bedrock-agentcore` package is a 0.0.1 placeholder with no
usable exports, so tests can't rely on it locally).
"""

import sys
import types


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
