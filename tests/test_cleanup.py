"""Tests for cleanup utility service."""
import pytest
import os
import tempfile
from app.services.cleanup import (
    TempFileManager,
    temp_file_manager,
    safe_unlink,
    safe_rmtree,
)


class TestTempFileManager:
    def test_create_temp_file(self):
        manager = TempFileManager()
        path = manager.create_temp_file(suffix=".txt")
        
        assert os.path.exists(path)
        assert path.endswith(".txt")
        
        # Cleanup
        manager.cleanup()
        assert not os.path.exists(path)

    def test_create_temp_dir(self):
        manager = TempFileManager()
        path = manager.create_temp_dir()
        
        assert os.path.exists(path)
        assert os.path.isdir(path)
        
        # Cleanup
        manager.cleanup()
        assert not os.path.exists(path)

    def test_add_file(self):
        manager = TempFileManager()
        
        # Create a real temp file
        fd, path = tempfile.mkstemp()
        os.close(fd)
        
        manager.add_file(path)
        manager.cleanup()
        
        assert not os.path.exists(path)

    def test_add_nonexistent_file_ignored(self):
        manager = TempFileManager()
        manager.add_file("/nonexistent/path.txt")
        manager.cleanup()  # Should not raise

    def test_context_manager(self):
        with temp_file_manager() as manager:
            path = manager.create_temp_file(suffix=".txt")
            assert os.path.exists(path)
        
        # Should be cleaned up after context
        assert not os.path.exists(path)

    def test_context_manager_with_exception(self):
        try:
            with temp_file_manager() as manager:
                path = manager.create_temp_file(suffix=".txt")
                assert os.path.exists(path)
                raise ValueError("Test exception")
        except ValueError:
            pass
        
        # Should still be cleaned up
        assert not os.path.exists(path)


class TestSafeUnlink:
    def test_safe_unlink_existing_file(self):
        fd, path = tempfile.mkstemp()
        os.close(fd)
        assert os.path.exists(path)
        
        safe_unlink(path)
        assert not os.path.exists(path)

    def test_safe_unlink_nonexistent_file(self):
        safe_unlink("/nonexistent/path.txt")  # Should not raise

    def test_safe_unlink_none(self):
        safe_unlink(None)  # Should not raise


class TestSafeRmtree:
    def test_safe_rmtree_existing_dir(self):
        path = tempfile.mkdtemp()
        assert os.path.exists(path)
        
        safe_rmtree(path)
        assert not os.path.exists(path)

    def test_safe_rmtree_nonexistent_dir(self):
        safe_rmtree("/nonexistent/path")  # Should not raise

    def test_safe_rmtree_none(self):
        safe_rmtree(None)  # Should not raise