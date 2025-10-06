#!/usr/bin/env python3
"""Comprehensive test suite for the file watcher functionality."""

import asyncio
import json
import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Dict, Any
import unittest
from unittest.mock import patch, AsyncMock

from watch_and_load import MemoryWatcher, MemoryFileHandler
from load_memory_batch import BatchMemoryLoader


class TestFileWatcher(unittest.TestCase):
    """Test cases for the file watcher system."""
    
    def setUp(self):
        """Set up test environment."""
        # Create temporary directories for testing
        self.test_dir = Path(tempfile.mkdtemp())
        self.watch_folder = self.test_dir / "test-memory-drops"
        self.processed_log = self.test_dir / "test_processed_files.json"
        
        # Create watch folder
        self.watch_folder.mkdir(exist_ok=True)
        
        print(f"🧪 Test setup complete")
        print(f"   Watch folder: {self.watch_folder}")
        print(f"   Processed log: {self.processed_log}")
    
    def tearDown(self):
        """Clean up test environment."""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
        print("🗑️  Test cleanup complete")
    
    def create_test_file(self, filename: str, content: str, metadata: Dict[str, Any] = None) -> Path:
        """Create a test file with optional metadata."""
        filepath = self.watch_folder / filename
        
        # Write content file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Write metadata file if provided
        if metadata:
            meta_file = filepath.with_suffix(filepath.suffix + '.meta.json')
            with open(meta_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)
        
        return filepath
    
    def test_file_handler_initialization(self):
        """Test MemoryFileHandler initialization."""
        print("\n🔧 Testing file handler initialization...")
        
        handler = MemoryFileHandler(str(self.watch_folder), str(self.processed_log))
        
        self.assertEqual(handler.watch_folder, self.watch_folder)
        self.assertEqual(handler.processed_log, self.processed_log)
        self.assertEqual(handler.supported_extensions, {'.txt', '.md', '.json'})
        self.assertIsInstance(handler.processed_files, dict)
        
        print("   ✅ Handler initialized correctly")
    
    def test_should_process_file(self):
        """Test file processing decision logic."""
        print("\n📋 Testing file processing logic...")
        
        handler = MemoryFileHandler(str(self.watch_folder), str(self.processed_log))
        
        # Test supported extensions
        test_file = self.create_test_file("test.md", "Test content")
        self.assertTrue(handler.should_process_file(test_file))
        print("   ✅ Supported file extension (.md) - should process")
        
        # Test unsupported extensions
        unsupported_file = self.create_test_file("test.pdf", "Test content")
        self.assertFalse(handler.should_process_file(unsupported_file))
        print("   ✅ Unsupported file extension (.pdf) - should not process")
        
        # Test metadata files
        meta_file = self.create_test_file("test.md.meta.json", '{"source": "test"}')
        self.assertFalse(handler.should_process_file(meta_file))
        print("   ✅ Metadata file (.meta.json) - should not process")
    
    def test_metadata_loading(self):
        """Test metadata file loading."""
        print("\n📋 Testing metadata loading...")
        
        handler = MemoryFileHandler(str(self.watch_folder), str(self.processed_log))
        
        # Test file without metadata
        test_file = self.create_test_file("no_meta.md", "Test content")
        metadata = handler.load_metadata(test_file)
        
        expected_default = {
            'source': 'manual',
            'tags': [],
            'importance': 1
        }
        self.assertEqual(metadata, expected_default)
        print("   ✅ Default metadata loaded for file without .meta.json")
        
        # Test file with metadata
        test_metadata = {
            'source': 'chat',
            'tags': ['test', 'automation'],
            'importance': 3
        }
        test_file_with_meta = self.create_test_file(
            "with_meta.md", 
            "Test content with metadata",
            test_metadata
        )
        
        loaded_metadata = handler.load_metadata(test_file_with_meta)
        self.assertEqual(loaded_metadata, test_metadata)
        print("   ✅ Custom metadata loaded correctly")
    
    def test_file_hash_detection(self):
        """Test file change detection using hashes."""
        print("\n🔍 Testing file change detection...")
        
        handler = MemoryFileHandler(str(self.watch_folder), str(self.processed_log))
        
        # Create test file
        test_file = self.create_test_file("hash_test.md", "Original content")
        original_hash = handler.get_file_hash(test_file)
        
        # Modify file
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write("Modified content")
        
        modified_hash = handler.get_file_hash(test_file)
        
        self.assertNotEqual(original_hash, modified_hash)
        print("   ✅ File hash changes detected correctly")
    
    @patch('watch_and_load.BatchMemoryLoader')
    async def test_file_processing_async(self, mock_loader_class):
        """Test asynchronous file processing."""
        print("\n⚡ Testing async file processing...")

        # Mock the loader
        mock_loader = AsyncMock()

        # Mock the process_file method to set successful_inserts after processing
        async def mock_process_file(*args, **kwargs):
            mock_loader.successful_inserts = 2
            mock_loader.failed_inserts = 0

        mock_loader.process_file.side_effect = mock_process_file
        mock_loader_class.return_value = mock_loader

        handler = MemoryFileHandler(str(self.watch_folder), str(self.processed_log))
        # Replace the handler's loader with our mock
        handler.loader = mock_loader

        # Create test file with metadata
        test_file = self.create_test_file(
            "async_test.md",
            "Test content for async processing",
            {'source': 'test', 'tags': ['async'], 'importance': 2}
        )

        # Process file
        result = await handler.process_file_async(test_file)

        # Verify processing
        self.assertTrue(result)
        mock_loader.process_file.assert_called_once()

        # Check processed files log
        file_key = str(test_file.relative_to(self.watch_folder))
        self.assertIn(file_key, handler.processed_files)

        processed_info = handler.processed_files[file_key]
        self.assertEqual(processed_info['source'], 'test')
        self.assertEqual(processed_info['tags'], ['async'])
        self.assertEqual(processed_info['importance'], 2)
        self.assertEqual(processed_info['chunks'], 2)

        print("   ✅ Async file processing completed successfully")
    
    def test_processed_log_persistence(self):
        """Test processed files log saving and loading."""
        print("\n💾 Testing processed log persistence...")
        
        handler = MemoryFileHandler(str(self.watch_folder), str(self.processed_log))
        
        # Add some processed file data
        test_data = {
            'test.md': {
                'processed_at': '2025-01-15T10:30:00',
                'hash': 'abc123',
                'chunks': 3,
                'source': 'test',
                'tags': ['persistence'],
                'importance': 2
            }
        }
        
        handler.processed_files = test_data
        handler.save_processed_log()
        
        # Verify file was created
        self.assertTrue(self.processed_log.exists())
        
        # Create new handler and verify data loads
        new_handler = MemoryFileHandler(str(self.watch_folder), str(self.processed_log))
        self.assertEqual(new_handler.processed_files, test_data)
        
        print("   ✅ Processed log persistence working correctly")


class TestWatcherIntegration(unittest.TestCase):
    """Integration tests for the complete watcher system."""
    
    def setUp(self):
        """Set up integration test environment."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.watch_folder = self.test_dir / "integration-test-drops"
        self.processed_log = self.test_dir / "integration_processed.json"
        
        # Create watch folder
        self.watch_folder.mkdir(exist_ok=True)
        
        print(f"🔧 Integration test setup complete")
        print(f"   Watch folder: {self.watch_folder}")
    
    def tearDown(self):
        """Clean up integration test environment."""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
        print("🗑️  Integration test cleanup complete")
    
    @patch('watch_and_load.BatchMemoryLoader')
    async def test_existing_files_processing(self, mock_loader_class):
        """Test processing of existing files on startup."""
        print("\n📁 Testing existing files processing...")

        # Mock the loader
        mock_loader = AsyncMock()
        mock_loader.successful_inserts = 1
        mock_loader.failed_inserts = 0
        mock_loader_class.return_value = mock_loader

        # Create some existing files
        existing_files = [
            ("existing1.md", "Content 1"),
            ("existing2.txt", "Content 2"),
            ("existing3.json", '{"test": "data"}')
        ]

        for filename, content in existing_files:
            filepath = self.watch_folder / filename
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)

        # Create watcher
        watcher = MemoryWatcher(str(self.watch_folder), str(self.processed_log))
        # Replace the handler's loader with our mock
        watcher.handler.loader = mock_loader

        # Process existing files
        await watcher.process_existing_files()

        # Verify all files were processed
        self.assertEqual(mock_loader.process_file.call_count, len(existing_files))

        print(f"   ✅ Processed {len(existing_files)} existing files")


async def run_async_tests():
    """Run async test methods."""
    print("🚀 Running async tests...")
    
    # File processing tests
    test_case = TestFileWatcher()
    test_case.setUp()
    
    try:
        await test_case.test_file_processing_async()
    finally:
        test_case.tearDown()
    
    # Integration tests
    integration_test = TestWatcherIntegration()
    integration_test.setUp()
    
    try:
        await integration_test.test_existing_files_processing()
    finally:
        integration_test.tearDown()


def main():
    """Run all tests."""
    print("🧪 Starting File Watcher Test Suite")
    print("=" * 60)
    
    # Run synchronous tests
    print("\n📋 Running synchronous tests...")
    
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add test cases
    suite.addTest(TestFileWatcher('test_file_handler_initialization'))
    suite.addTest(TestFileWatcher('test_should_process_file'))
    suite.addTest(TestFileWatcher('test_metadata_loading'))
    suite.addTest(TestFileWatcher('test_file_hash_detection'))
    suite.addTest(TestFileWatcher('test_processed_log_persistence'))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=0)
    result = runner.run(suite)
    
    # Run async tests
    print("\n⚡ Running async tests...")
    asyncio.run(run_async_tests())
    
    # Summary
    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("🎉 All file watcher tests passed!")
        print("\n✅ File watcher system is ready for production")
        return True
    else:
        print("❌ Some tests failed!")
        print(f"   Failures: {len(result.failures)}")
        print(f"   Errors: {len(result.errors)}")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
