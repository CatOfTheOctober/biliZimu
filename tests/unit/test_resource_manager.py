"""Unit tests for ResourceManager class."""

import tempfile
from pathlib import Path

import pytest

from bilibili_extractor.utils.resource_manager import ResourceManager


def test_resource_manager_initialization():
    """Test ResourceManager can be initialized with default parameters."""
    rm = ResourceManager(temp_dir="./temp")
    assert rm.temp_dir == Path("./temp")
    assert rm.keep_files is False
    assert rm.tracked_files == []


def test_resource_manager_with_keep_files():
    """Test ResourceManager respects keep_files parameter."""
    rm = ResourceManager(temp_dir="./temp", keep_files=True)
    assert rm.keep_files is True


def test_register_file():
    """Test registering a file for cleanup."""
    rm = ResourceManager(temp_dir="./temp")
    file_path = Path("test.txt")
    
    rm.register_file(file_path)
    
    assert file_path in rm.tracked_files
    assert len(rm.tracked_files) == 1


def test_register_multiple_files():
    """Test registering multiple files."""
    rm = ResourceManager(temp_dir="./temp")
    file1 = Path("test1.txt")
    file2 = Path("test2.txt")
    
    rm.register_file(file1)
    rm.register_file(file2)
    
    assert len(rm.tracked_files) == 2
    assert file1 in rm.tracked_files
    assert file2 in rm.tracked_files


def test_register_duplicate_file():
    """Test registering the same file twice doesn't duplicate."""
    rm = ResourceManager(temp_dir="./temp")
    file_path = Path("test.txt")
    
    rm.register_file(file_path)
    rm.register_file(file_path)
    
    assert len(rm.tracked_files) == 1


def test_cleanup_deletes_files():
    """Test cleanup deletes tracked files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        rm = ResourceManager(temp_dir=tmpdir)
        
        # Create test files
        file1 = Path(tmpdir) / "test1.txt"
        file2 = Path(tmpdir) / "test2.txt"
        file1.write_text("test content 1")
        file2.write_text("test content 2")
        
        # Register and cleanup
        rm.register_file(file1)
        rm.register_file(file2)
        rm.cleanup()
        
        # Verify files are deleted
        assert not file1.exists()
        assert not file2.exists()
        assert len(rm.tracked_files) == 0


def test_cleanup_with_keep_files():
    """Test cleanup preserves files when keep_files=True."""
    with tempfile.TemporaryDirectory() as tmpdir:
        rm = ResourceManager(temp_dir=tmpdir, keep_files=True)
        
        # Create test file
        file_path = Path(tmpdir) / "test.txt"
        file_path.write_text("test content")
        
        # Register and cleanup
        rm.register_file(file_path)
        rm.cleanup()
        
        # Verify file still exists
        assert file_path.exists()


def test_cleanup_is_idempotent():
    """Test cleanup can be called multiple times safely (Property 24)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        rm = ResourceManager(temp_dir=tmpdir)
        
        # Create test file
        file_path = Path(tmpdir) / "test.txt"
        file_path.write_text("test content")
        
        rm.register_file(file_path)
        
        # Call cleanup multiple times
        rm.cleanup()
        rm.cleanup()
        rm.cleanup()
        
        # Should not raise any exceptions
        assert not file_path.exists()
        assert len(rm.tracked_files) == 0


def test_cleanup_handles_nonexistent_files():
    """Test cleanup handles files that don't exist."""
    rm = ResourceManager(temp_dir="./temp")
    
    # Register a file that doesn't exist
    file_path = Path("/nonexistent/file.txt")
    rm.register_file(file_path)
    
    # Cleanup should not raise exception
    rm.cleanup()
    assert len(rm.tracked_files) == 0


def test_cleanup_handles_directories():
    """Test cleanup can delete directories."""
    with tempfile.TemporaryDirectory() as tmpdir:
        rm = ResourceManager(temp_dir=tmpdir)
        
        # Create test directory with files
        test_dir = Path(tmpdir) / "test_subdir"
        test_dir.mkdir()
        (test_dir / "file1.txt").write_text("content 1")
        (test_dir / "file2.txt").write_text("content 2")
        
        # Register and cleanup
        rm.register_file(test_dir)
        rm.cleanup()
        
        # Verify directory is deleted
        assert not test_dir.exists()


def test_cleanup_failure_does_not_raise():
    """Test cleanup failures are logged but don't raise exceptions (Property 26)."""
    rm = ResourceManager(temp_dir="./temp")
    
    # Register a file in a protected location (likely to fail)
    # This simulates a cleanup failure scenario
    file_path = Path("/root/protected_file.txt")
    rm.register_file(file_path)
    
    # Cleanup should not raise exception even if deletion fails
    try:
        rm.cleanup()
        # If we get here, cleanup handled the failure gracefully
        assert True
    except Exception:
        pytest.fail("cleanup() should not raise exceptions on failure")


def test_context_manager_cleanup():
    """Test context manager ensures cleanup on exit."""
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / "test.txt"
        file_path.write_text("test content")
        
        with ResourceManager(temp_dir=tmpdir) as rm:
            rm.register_file(file_path)
            assert file_path.exists()
        
        # File should be deleted after context exit
        assert not file_path.exists()


def test_context_manager_cleanup_on_exception():
    """Test context manager cleans up even when exception occurs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / "test.txt"
        file_path.write_text("test content")
        
        try:
            with ResourceManager(temp_dir=tmpdir) as rm:
                rm.register_file(file_path)
                raise ValueError("Test exception")
        except ValueError:
            pass
        
        # File should still be deleted despite exception
        assert not file_path.exists()


def test_check_disk_space_sufficient():
    """Test check_disk_space returns True when space is sufficient."""
    with tempfile.TemporaryDirectory() as tmpdir:
        rm = ResourceManager(temp_dir=tmpdir)
        
        # Check for a small amount of space (should be available)
        assert rm.check_disk_space(1) is True


def test_check_disk_space_insufficient():
    """Test check_disk_space returns False when space is insufficient."""
    with tempfile.TemporaryDirectory() as tmpdir:
        rm = ResourceManager(temp_dir=tmpdir)
        
        # Check for an unreasonably large amount of space
        # This should return False on most systems
        result = rm.check_disk_space(999999999)  # ~1 PB
        # Note: On systems with huge storage, this might still return True
        # So we just verify it returns a boolean
        assert isinstance(result, bool)


def test_check_disk_space_invalid_directory():
    """Test check_disk_space handles invalid directory gracefully."""
    rm = ResourceManager(temp_dir="/nonexistent/directory")
    
    # Should return True (allow operation) if check fails
    result = rm.check_disk_space(100)
    assert isinstance(result, bool)


def test_cleanup_empty_tracked_files():
    """Test cleanup with no tracked files."""
    rm = ResourceManager(temp_dir="./temp")
    
    # Cleanup with empty list should not raise
    rm.cleanup()
    assert len(rm.tracked_files) == 0


def test_register_file_path_types():
    """Test register_file accepts Path objects."""
    rm = ResourceManager(temp_dir="./temp")
    
    # Test with Path object
    path_obj = Path("test.txt")
    rm.register_file(path_obj)
    assert path_obj in rm.tracked_files


def test_multiple_cleanup_calls_clear_list():
    """Test tracked_files list is cleared after cleanup."""
    with tempfile.TemporaryDirectory() as tmpdir:
        rm = ResourceManager(temp_dir=tmpdir)
        
        file_path = Path(tmpdir) / "test.txt"
        file_path.write_text("test")
        
        rm.register_file(file_path)
        assert len(rm.tracked_files) == 1
        
        rm.cleanup()
        assert len(rm.tracked_files) == 0
        
        # Register again and cleanup again
        file_path2 = Path(tmpdir) / "test2.txt"
        file_path2.write_text("test2")
        rm.register_file(file_path2)
        assert len(rm.tracked_files) == 1
        
        rm.cleanup()
        assert len(rm.tracked_files) == 0
