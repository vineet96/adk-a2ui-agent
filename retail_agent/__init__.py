"""
retail_agent package.
Applies session_id patches before the agent is loaded so the fixes
are in place when Agent Engine / Agentspace calls into the ADK runtime.
"""
from . import patches as _patches
_patches.apply()

from . import agent  # noqa: E402 — must come after patches
