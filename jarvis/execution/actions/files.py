"""File operations action group matching 08_ACTION_ENGINE.md and 09_TOOL_REGISTRY.md."""

from typing import Dict, List, Optional
from jarvis.policy.safety import RiskLevel
from jarvis.registry.registry import Availability, ToolDeclaration, ToolRegistry


class VirtualFileManager:
    """Stateful file system manager with verification hooks."""

    def __init__(self):
        self.files: Dict[str, str] = {
            "document.txt": "Sample document content",
            "project.zip": "Binary zip data",
            "report.pdf": "PDF report data",
        }
        self.opened_files: set[str] = set()
        self.fail_next_verification: bool = False

    def open_file(self, path: str) -> str:
        clean = path.strip()
        if clean not in self.files:
            raise FileNotFoundError(f"File not found: {path}")
        self.opened_files.add(clean)
        return f"File '{clean}' opened."

    def verify_file_opened(self, path: str) -> bool:
        if self.fail_next_verification:
            self.fail_next_verification = False
            return False
        return path.strip() in self.opened_files

    def create_file(self, path: str, content: str = "") -> str:
        clean = path.strip()
        self.files[clean] = content
        return f"File '{clean}' created successfully."

    def verify_file_created(self, path: str, content: str = "") -> bool:
        if self.fail_next_verification:
            self.fail_next_verification = False
            return False
        return path.strip() in self.files

    def copy_file(self, source: str, destination: str) -> str:
        src = source.strip()
        dst = destination.strip()
        if src not in self.files:
            raise FileNotFoundError(f"Source file not found: {source}")
        self.files[dst] = self.files[src]
        return f"Copied '{src}' to '{dst}'."

    def verify_file_copied(self, source: str, destination: str) -> bool:
        if self.fail_next_verification:
            self.fail_next_verification = False
            return False
        return destination.strip() in self.files

    def move_file(self, source: str, destination: str) -> str:
        src = source.strip()
        dst = destination.strip()
        if src not in self.files:
            raise FileNotFoundError(f"Source file not found: {source}")
        self.files[dst] = self.files.pop(src)
        return f"Moved '{src}' to '{dst}'."

    def verify_file_moved(self, source: str, destination: str) -> bool:
        if self.fail_next_verification:
            self.fail_next_verification = False
            return False
        return destination.strip() in self.files and source.strip() not in self.files

    def delete_file(self, path: str) -> str:
        clean = path.strip()
        if clean in self.files:
            del self.files[clean]
        if clean in self.opened_files:
            self.opened_files.remove(clean)
        return f"File '{clean}' deleted permanently."

    def verify_file_deleted(self, path: str) -> bool:
        if self.fail_next_verification:
            self.fail_next_verification = False
            return False
        return path.strip() not in self.files


_DEFAULT_FILE_MANAGER = VirtualFileManager()


def get_default_file_manager() -> VirtualFileManager:
    return _DEFAULT_FILE_MANAGER


def register_file_tools(registry: ToolRegistry, manager: Optional[VirtualFileManager] = None) -> None:
    """Register file operation tools into ToolRegistry."""
    m = manager or _DEFAULT_FILE_MANAGER

    # open_file tool
    open_decl = ToolDeclaration(
        name="open_file",
        version=1,
        description="Open an existing file",
        input_schema={"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
        output_schema={"type": "string"},
        risk_level=RiskLevel.LOW,
        required_permissions=["filesystem.read"],
        availability=Availability.OFFLINE,
        reversible=True,
        verification_method="check_file_opened",
    )
    registry.register_tool(open_decl, handler=m.open_file, verifier=m.verify_file_opened)

    # create_file tool
    create_decl = ToolDeclaration(
        name="create_file",
        version=1,
        description="Create a new file with optional content",
        input_schema={
            "type": "object",
            "properties": {"path": {"type": "string"}, "content": {"type": "string", "default": ""}},
            "required": ["path"],
        },
        output_schema={"type": "string"},
        risk_level=RiskLevel.LOW,
        required_permissions=["filesystem.write"],
        availability=Availability.OFFLINE,
        reversible=True,
        verification_method="check_file_exists",
    )
    registry.register_tool(create_decl, handler=m.create_file, verifier=m.verify_file_created)

    # copy_file tool
    copy_decl = ToolDeclaration(
        name="copy_file",
        version=1,
        description="Copy a file from source to destination",
        input_schema={
            "type": "object",
            "properties": {"source": {"type": "string"}, "destination": {"type": "string"}},
            "required": ["source", "destination"],
        },
        output_schema={"type": "string"},
        risk_level=RiskLevel.LOW,
        required_permissions=["filesystem.read", "filesystem.write"],
        availability=Availability.OFFLINE,
        reversible=True,
        verification_method="check_file_copied",
    )
    registry.register_tool(copy_decl, handler=m.copy_file, verifier=m.verify_file_copied)

    # move_file tool
    move_decl = ToolDeclaration(
        name="move_file",
        version=1,
        description="Move or rename a file from source to destination",
        input_schema={
            "type": "object",
            "properties": {"source": {"type": "string"}, "destination": {"type": "string"}},
            "required": ["source", "destination"],
        },
        output_schema={"type": "string"},
        risk_level=RiskLevel.LOW,
        required_permissions=["filesystem.read", "filesystem.write"],
        availability=Availability.OFFLINE,
        reversible=True,
        verification_method="check_file_moved",
    )
    registry.register_tool(move_decl, handler=m.move_file, verifier=m.verify_file_moved)

    # delete_file tool (HIGH risk)
    delete_decl = ToolDeclaration(
        name="delete_file",
        version=1,
        description="Delete a file permanently (High Risk)",
        input_schema={"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
        output_schema={"type": "string"},
        risk_level=RiskLevel.HIGH,
        required_permissions=["filesystem.delete"],
        availability=Availability.OFFLINE,
        reversible=False,
        verification_method="check_file_deleted",
    )
    registry.register_tool(delete_decl, handler=m.delete_file, verifier=m.verify_file_deleted)
