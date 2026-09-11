"""Tests for MemoryStore and schema compliance matching 12_MEMORY_SCHEMA.md."""

import tempfile
import pytest
from jarvis.core.errors import ErrorCode, JarvisError
from jarvis.memory.models import MemoryCategory, MemoryLifecycle
from jarvis.memory.store import MemoryStore


def test_memory_store_write_read_and_schema():
    store = MemoryStore()
    item = store.write(key="preferred_browser", value="Chrome", category=MemoryCategory.PREFERENCE)
    assert item.key == "preferred_browser"
    assert item.value == "Chrome"
    assert item.category == MemoryCategory.PREFERENCE
    assert item.source == "user"
    assert item.confidence == 1.0
    assert item.lifecycle == MemoryLifecycle.ACTIVE
    assert item.created_at is not None
    assert item.updated_at is not None

    fetched = store.read("preferred_browser")
    assert fetched is not None
    assert fetched.value == "Chrome"


def test_memory_store_update():
    store = MemoryStore()
    store.write(key="preferred_browser", value="Chrome")
    updated = store.update(key="preferred_browser", value="Firefox")
    assert updated.value == "Firefox"
    assert store.read("preferred_browser").value == "Firefox"


def test_memory_store_update_nonexistent_raises_e400():
    store = MemoryStore()
    with pytest.raises(JarvisError) as exc_info:
        store.update(key="non_existent", value="val")
    assert exc_info.value.code == ErrorCode.E400


def test_memory_store_forget():
    store = MemoryStore()
    store.write(key="temp_project", value="alpha")
    assert store.read("temp_project") is not None

    forgotten = store.forget("temp_project")
    assert forgotten is True
    assert store.read("temp_project") is None


def test_memory_store_secret_rejection():
    store = MemoryStore()
    # 1. Key contains password
    with pytest.raises(JarvisError) as exc_info:
        store.write(key="my_password", value="12345")
    assert exc_info.value.code == ErrorCode.E400

    # 2. Value contains api_key
    with pytest.raises(JarvisError) as exc_info:
        store.write(key="openai_config", value={"api_key": "sk-123456789"})
    assert exc_info.value.code == ErrorCode.E400

    # 3. Value string contains bearer token
    with pytest.raises(JarvisError) as exc_info:
        store.write(key="auth", value="Bearer eyJhbGciOi...")
    assert exc_info.value.code == ErrorCode.E400


def test_memory_store_persistence_file():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        tmp_path = tmp.name

    store1 = MemoryStore(persistence_file=tmp_path)
    store1.write(key="theme", value="dark", category=MemoryCategory.PREFERENCE)

    # Reload in new instance
    store2 = MemoryStore(persistence_file=tmp_path)
    item = store2.read("theme")
    assert item is not None
    assert item.value == "dark"


def test_memory_store_list_by_category():
    store = MemoryStore()
    store.write(key="pref1", value="a", category=MemoryCategory.PREFERENCE)
    store.write(key="dev1", value="laptop", category=MemoryCategory.DEVICE)
    store.write(key="pref2", value="b", category=MemoryCategory.PREFERENCE)

    prefs = store.list_by_category(MemoryCategory.PREFERENCE)
    assert len(prefs) == 2
    assert {p.key for p in prefs} == {"pref1", "pref2"}
