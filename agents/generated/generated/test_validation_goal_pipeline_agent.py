from __future__ import annotations
import importlib.util
import pathlib
import pytest

AGENT_FILE = pathlib.Path('/etc/neron/workspace/agents/validation_goal_pipeline_agent.py')

def load_agent():
    spec = importlib.util.spec_from_file_location('generated_agent_under_test', AGENT_FILE)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module.Agent()

@pytest.mark.asyncio
async def test_agent_execute_returns_response():
    result = await load_agent().execute(text='combien de temps avant la WWDC ?')
    assert isinstance(result, dict)
    assert result.get('response')
    assert result.get('status') == 'ok'
