"""Action implementations."""

from jarvis.execution.actions.system import (
    VirtualSystemBackend,
    RealSystemBackend,
    register_system_tools,
)
from jarvis.execution.actions.application import (
    VirtualAppManager,
    RealAppManager,
    register_application_tools,
    get_default_app_manager,
)
from jarvis.execution.actions.input import (
    VirtualInputBackend,
    register_input_tools,
    get_default_input_backend,
)
from jarvis.execution.actions.window import (
    VirtualWindowManager,
    register_window_tools,
    get_default_window_manager,
)
from jarvis.execution.actions.media import (
    VirtualMediaManager,
    register_media_tools,
    get_default_media_manager,
)
from jarvis.execution.actions.files import (
    VirtualFileManager,
    register_file_tools,
    get_default_file_manager,
)

__all__ = [
    "VirtualSystemBackend",
    "RealSystemBackend",
    "register_system_tools",
    "VirtualAppManager",
    "RealAppManager",
    "register_application_tools",
    "get_default_app_manager",
    "VirtualInputBackend",
    "register_input_tools",
    "get_default_input_backend",
    "VirtualWindowManager",
    "register_window_tools",
    "get_default_window_manager",
    "VirtualMediaManager",
    "register_media_tools",
    "get_default_media_manager",
    "VirtualFileManager",
    "register_file_tools",
    "get_default_file_manager",
]
