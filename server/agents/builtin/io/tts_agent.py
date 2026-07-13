"""Legacy TTS agent facade.

The implementation lives in :mod:`voice`; this module keeps the historic
``agents.builtin.io.tts_agent`` import path used by Core and Gateway.
"""

from voice.adapters.legacy_agents import TTSAgent, load_tts_engine as load_engine
