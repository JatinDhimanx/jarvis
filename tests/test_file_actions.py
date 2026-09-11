"""Tests for File actions matching 08_ACTION_ENGINE.md and 11_SAFETY_AND_PERMISSIONS.md."""

import pytest
from jarvis.execution.action_engine import ActionRequest, ActionStatus
from jarvis.execution.actions.files import VirtualFileManager
from jarvis.pipeline import ExecutionPipeline


def test_file_manager_crud_operations():
    """Test create, copy, move, open, and delete."""
    fm = VirtualFileManager()

    # create_file
    res1 = fm.create_file("test.py", "print('hello')")
    assert "test.py" in res1
    assert fm.verify_file_created("test.py") is True
    assert fm.files["test.py"] == "print('hello')"

    # copy_file
    res2 = fm.copy_file("test.py", "test_copy.py")
    assert "test_copy.py" in res2
    assert fm.verify_file_copied("test.py", "test_copy.py") is True

    # move_file
    res3 = fm.move_file("test_copy.py", "test_moved.py")
    assert "test_moved.py" in res3
    assert fm.verify_file_moved("test_copy.py", "test_moved.py") is True

    # open_file
    res4 = fm.open_file("test.py")
    assert "opened" in res4
    assert fm.verify_file_opened("test.py") is True


def test_file_not_found_handling():
    """Opening or copying missing file raises error and returns failed action with E510."""
    fm = VirtualFileManager()
    pipeline = ExecutionPipeline(file_manager=fm)

    req = ActionRequest(
        action_id="a-file1",
        session_id="s-test",
        source_event_id="e-test",
        source="voice",
        action="open_file",
        parameters={"path": "nonexistent.txt"},
    )
    result = pipeline.action_engine.execute(req)
    assert result.status == ActionStatus.FAILED
    assert result.error_code == "E510"
    assert "not found" in result.result


def test_delete_file_high_risk_confirmation_flow():
    """Per 11_SAFETY_AND_PERMISSIONS.md: delete_file is HIGH risk requiring confirmation."""
    fm = VirtualFileManager()
    pipeline = ExecutionPipeline(file_manager=fm)

    assert "project.zip" in fm.files

    req = ActionRequest(
        action_id="a-file2",
        session_id="s-test",
        source_event_id="e-test",
        source="voice",
        action="delete_file",
        parameters={"path": "project.zip"},
    )

    # 1. First execution requires confirmation
    res1 = pipeline.action_engine.execute(req, user_confirmed=False)
    assert res1.status == ActionStatus.NEEDS_CONFIRMATION
    assert "Delete 'project.zip' permanently? Confirm or cancel." in res1.result
    assert "project.zip" in fm.files  # File not deleted yet

    # 2. Confirmed execution deletes file
    res2 = pipeline.action_engine.execute(req, user_confirmed=True)
    assert res2.status == ActionStatus.SUCCESS
    assert res2.verified is True
    assert "project.zip" not in fm.files


def test_file_action_verification_failure():
    """Action executed but post-check fails verification -> E700."""
    fm = VirtualFileManager()
    fm.fail_next_verification = True
    pipeline = ExecutionPipeline(file_manager=fm)

    req = ActionRequest(
        action_id="a-file3",
        session_id="s-test",
        source_event_id="e-test",
        source="voice",
        action="create_file",
        parameters={"path": "note.txt", "content": "123"},
    )
    result = pipeline.action_engine.execute(req)
    assert result.status == ActionStatus.FAILED
    assert result.verified is False
    assert result.error_code == "E700"
