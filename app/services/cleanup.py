"""Cleanup utility service for temporary files."""
import os
import tempfile
import shutil
from typing import List
from contextlib import contextmanager


class TempFileManager:
    """Manages temporary files and ensures cleanup."""

    def __init__(self):
        self.temp_files: List[str] = []
        self.temp_dirs: List[str] = []

    def add_file(self, filepath: str):
        """Register a temporary file for cleanup."""
        if filepath and os.path.exists(filepath):
            self.temp_files.append(filepath)

    def add_dir(self, dirpath: str):
        """Register a temporary directory for cleanup."""
        if dirpath and os.path.exists(dirpath):
            self.temp_dirs.append(dirpath)

    def create_temp_file(self, suffix: str = "", prefix: str = "eligibility_") -> str:
        """Create and register a temporary file."""
        fd, path = tempfile.mkstemp(suffix=suffix, prefix=prefix)
        os.close(fd)
        self.add_file(path)
        return path

    def create_temp_dir(self, suffix: str = "", prefix: str = "eligibility_") -> str:
        """Create and register a temporary directory."""
        path = tempfile.mkdtemp(suffix=suffix, prefix=prefix)
        self.add_dir(path)
        return path

    def cleanup(self):
        """Clean up all registered temporary files and directories."""
        for filepath in self.temp_files:
            try:
                if os.path.exists(filepath):
                    os.unlink(filepath)
            except Exception as e:
                # Log but don't raise - cleanup should be best effort
                print(f"Warning: Failed to cleanup temp file {filepath}: {e}")

        for dirpath in self.temp_dirs:
            try:
                if os.path.exists(dirpath):
                    shutil.rmtree(dirpath)
            except Exception as e:
                print(f"Warning: Failed to cleanup temp dir {dirpath}: {e}")

        self.temp_files.clear()
        self.temp_dirs.clear()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()


@contextmanager
def temp_file_manager():
    """Context manager for temporary file management."""
    manager = TempFileManager()
    try:
        yield manager
    finally:
        manager.cleanup()


def safe_unlink(filepath: str):
    """Safely delete a file if it exists."""
    try:
        if filepath and os.path.exists(filepath):
            os.unlink(filepath)
    except Exception:
        pass


def safe_rmtree(dirpath: str):
    """Safely delete a directory if it exists."""
    try:
        if dirpath and os.path.exists(dirpath):
            shutil.rmtree(dirpath)
    except Exception:
        pass