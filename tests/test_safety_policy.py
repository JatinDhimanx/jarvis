"""Tests for Safety and Permissions policy matching 11_SAFETY_AND_PERMISSIONS.md."""

from jarvis.core.config import JarvisConfig, SafetySection
from jarvis.policy.safety import RiskLevel, SafetyPolicy


def test_low_risk_actions_no_confirmation():
    """LOW risk actions (set_volume, open_app, move_mouse) do not require confirmation."""
    policy = SafetyPolicy()
    for act in ["set_volume", "open_app", "mute", "click", "play_pause"]:
        decision = policy.evaluate(act)
        assert decision.risk == RiskLevel.LOW
        assert decision.requires_confirmation is False


def test_high_risk_actions_require_confirmation():
    """HIGH risk actions (shutdown, delete_file) require confirmation when configured."""
    policy = SafetyPolicy()
    for act in ["shutdown", "delete_file"]:
        decision = policy.evaluate(act, {"path": "document.txt"})
        assert decision.risk == RiskLevel.HIGH
        assert decision.requires_confirmation is True
        assert decision.confirmation_prompt is not None
        assert "Confirm or cancel" in decision.confirmation_prompt


def test_confirmation_gated_by_config():
    """Verify require_confirmation flags in config strictly gate confirmation."""
    cfg = JarvisConfig(
        safety=SafetySection(require_confirmation_for_medium=False, require_confirmation_for_high=False)
    )
    policy = SafetyPolicy(cfg)

    # When high risk confirmation is explicitly disabled in config
    dec_high = policy.evaluate("shutdown")
    assert dec_high.risk == RiskLevel.HIGH
    assert dec_high.requires_confirmation is False


def test_specific_confirmation_prompts():
    """Per 11_SAFETY_AND_PERMISSIONS.md: never generic 'Are you sure?', must be specific."""
    policy = SafetyPolicy()

    prompt_del = policy.generate_confirmation_prompt("delete_file", {"path": "report.pdf"})
    assert prompt_del == "Delete 'report.pdf' permanently? Confirm or cancel."
    assert "Are you sure?" not in prompt_del

    prompt_shutdown = policy.generate_confirmation_prompt("shutdown", {})
    assert prompt_shutdown == "Shut down the computer now? Confirm or cancel."
