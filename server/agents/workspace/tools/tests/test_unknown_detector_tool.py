from __future__ import annotations

import importlib.util

from tools.models import ToolResult


def test_generated_tool_returns_tool_result():
    spec = importlib.util.spec_from_file_location("generated_tool", '/srv/homelab/server-1/neronOS/workspace/tools/unknown_detector_tool.py')
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    result = module.execute({"items": ["ok", "ERROR failed"]})
    assert isinstance(result, ToolResult)
    assert result.ok is True
    assert result.response or result.data
