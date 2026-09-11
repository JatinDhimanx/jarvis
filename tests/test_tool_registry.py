"""Tests for Tool Registry matching 09_TOOL_REGISTRY.md."""

import pytest
from jarvis.core.errors import ErrorCode, JarvisError
from jarvis.policy.safety import RiskLevel
from jarvis.registry.registry import Availability, ToolDeclaration, ToolRegistry


def test_tool_declaration_10_required_fields():
    """Verify tool declaration contains all 10 required fields per 09_TOOL_REGISTRY.md."""
    decl = ToolDeclaration(
        name="set_volume",
        version=1,
        description="Set volume",
        input_schema={"type": "object"},
        output_schema={"type": "string"},
        risk_level=RiskLevel.LOW,
        required_permissions=[],
        availability=Availability.OFFLINE,
        reversible=True,
        verification_method="read_audio_endpoint_volume",
    )
    assert decl.name == "set_volume"
    assert decl.version == 1
    assert decl.description == "Set volume"
    assert decl.input_schema == {"type": "object"}
    assert decl.output_schema == {"type": "string"}
    assert decl.risk_level == RiskLevel.LOW
    assert decl.required_permissions == []
    assert decl.availability == Availability.OFFLINE
    assert decl.reversible is True
    assert decl.verification_method == "read_audio_endpoint_volume"


def test_registry_lookup_and_missing_tool():
    """Verify registry throws E400 when tool is not registered."""
    reg = ToolRegistry()
    decl = ToolDeclaration(
        name="mock_tool",
        version=1,
        description="test",
        input_schema={},
        output_schema={},
        risk_level=RiskLevel.LOW,
        required_permissions=[],
        availability=Availability.OFFLINE,
        reversible=False,
        verification_method="none",
    )
    reg.register_tool(decl)

    assert reg.has_tool("mock_tool") is True
    assert reg.get_declaration("mock_tool").name == "mock_tool"

    with pytest.raises(JarvisError) as exc:
        reg.get_declaration("unregistered_tool")
    assert exc.value.code == ErrorCode.E400
