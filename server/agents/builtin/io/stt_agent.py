"""Legacy STT agent facade.

The implementation lives in :mod:`voice`; this module keeps the historic
``agents.builtin.io.stt_agent`` import path used by Core and Gateway.
"""

from voice.adapters.legacy_agents import STTAgent, load_stt_model as load_model
