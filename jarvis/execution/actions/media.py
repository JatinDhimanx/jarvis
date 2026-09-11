"""Media action group matching 08_ACTION_ENGINE.md and 09_TOOL_REGISTRY.md."""

from typing import List, Optional
from jarvis.policy.safety import RiskLevel
from jarvis.registry.registry import Availability, ToolDeclaration, ToolRegistry


class VirtualMediaManager:
    """Stateful virtual media playback manager with verification hooks."""

    def __init__(self):
        self.is_playing: bool = False
        self.playlist: List[str] = ["Track 1", "Track 2", "Track 3"]
        self.current_track_idx: int = 0
        self.fail_next_verification: bool = False

    def play_pause(self) -> str:
        self.is_playing = not self.is_playing
        state_str = "playing" if self.is_playing else "paused"
        return f"Media playback {state_str}."

    def verify_play_pause(self) -> bool:
        if self.fail_next_verification:
            self.fail_next_verification = False
            return False
        return True

    def next_track(self) -> str:
        self.current_track_idx = (self.current_track_idx + 1) % len(self.playlist)
        track = self.playlist[self.current_track_idx]
        return f"Playing next track: '{track}'."

    def verify_next_track(self) -> bool:
        if self.fail_next_verification:
            self.fail_next_verification = False
            return False
        return True

    def previous_track(self) -> str:
        self.current_track_idx = (self.current_track_idx - 1) % len(self.playlist)
        track = self.playlist[self.current_track_idx]
        return f"Playing previous track: '{track}'."

    def verify_previous_track(self) -> bool:
        if self.fail_next_verification:
            self.fail_next_verification = False
            return False
        return True


_DEFAULT_MEDIA_MANAGER = VirtualMediaManager()


def get_default_media_manager() -> VirtualMediaManager:
    return _DEFAULT_MEDIA_MANAGER


def register_media_tools(registry: ToolRegistry, manager: Optional[VirtualMediaManager] = None) -> None:
    """Register media playback tools into ToolRegistry."""
    m = manager or _DEFAULT_MEDIA_MANAGER

    # play_pause tool
    play_pause_decl = ToolDeclaration(
        name="play_pause",
        version=1,
        description="Toggle media playback between play and pause",
        input_schema={"type": "object"},
        output_schema={"type": "string"},
        risk_level=RiskLevel.LOW,
        required_permissions=[],
        availability=Availability.OFFLINE,
        reversible=True,
        verification_method="read_playback_status",
    )
    registry.register_tool(play_pause_decl, handler=m.play_pause, verifier=m.verify_play_pause)

    # next_track tool
    next_decl = ToolDeclaration(
        name="next_track",
        version=1,
        description="Skip to the next media track",
        input_schema={"type": "object"},
        output_schema={"type": "string"},
        risk_level=RiskLevel.LOW,
        required_permissions=[],
        availability=Availability.OFFLINE,
        reversible=False,
        verification_method="check_track_changed",
    )
    registry.register_tool(next_decl, handler=m.next_track, verifier=m.verify_next_track)

    # previous_track tool
    prev_decl = ToolDeclaration(
        name="previous_track",
        version=1,
        description="Return to the previous media track",
        input_schema={"type": "object"},
        output_schema={"type": "string"},
        risk_level=RiskLevel.LOW,
        required_permissions=[],
        availability=Availability.OFFLINE,
        reversible=False,
        verification_method="check_track_changed",
    )
    registry.register_tool(prev_decl, handler=m.previous_track, verifier=m.verify_previous_track)
