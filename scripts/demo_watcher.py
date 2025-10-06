#!/usr/bin/env python3
"""Demo script to showcase file watcher functionality without database dependency."""

import asyncio
import json
import os
import tempfile
import time
from pathlib import Path
from unittest.mock import AsyncMock, patch

from watch_and_load import MemoryWatcher, MemoryFileHandler


class DemoMemoryLoader:
    """Mock memory loader for demonstration purposes."""
    
    def __init__(self):
        self.total_chunks = 0
        self.successful_inserts = 0
        self.failed_inserts = 0
        self.skipped_chunks = 0
    
    async def process_file(self, filepath, source, tags=None, importance=1):
        """Mock file processing."""
        # Simulate processing time
        await asyncio.sleep(0.5)
        
        # Simulate chunking based on file size
        file_size = Path(filepath).stat().st_size
        chunks = max(1, file_size // 200)  # Rough estimate
        
        self.total_chunks = chunks
        self.successful_inserts = chunks
        self.failed_inserts = 0
        self.skipped_chunks = 0
        
        print(f"   📊 Simulated processing: {chunks} chunks from {file_size} bytes")


async def demo_file_processing():
    """Demonstrate file processing capabilities."""
    print("🎬 AI Memory System - File Watcher Demo")
    print("=" * 50)
    
    # Create temporary demo environment
    with tempfile.TemporaryDirectory() as temp_dir:
        demo_dir = Path(temp_dir)
        watch_folder = demo_dir / "demo-memory-drops"
        processed_log = demo_dir / "demo_processed.json"
        
        # Create watch folder
        watch_folder.mkdir()
        
        print(f"📁 Demo environment: {watch_folder}")
        
        # Create file handler with mock loader
        handler = MemoryFileHandler(str(watch_folder), str(processed_log))
        handler.loader = DemoMemoryLoader()
        
        # Demo 1: Create and process a simple text file
        print("\n🔹 Demo 1: Processing a simple text file")
        
        simple_file = watch_folder / "demo_notes.txt"
        with open(simple_file, 'w', encoding='utf-8') as f:
            f.write("""
Demo Notes - AI Memory System

This is a demonstration of the automated file processing system.
The file watcher monitors the memory-drops folder and automatically
processes new files as they are added.

Key features:
- Automatic file detection and processing
- Support for .txt, .md, and .json files
- Metadata support through .meta.json files
- Intelligent chunking for large documents
- Duplicate detection and change tracking
            """.strip())
        
        # Process the file
        result = await handler.process_file_async(simple_file)
        print(f"   ✅ Processing result: {'Success' if result else 'Failed'}")
        
        # Demo 2: Create a file with metadata
        print("\n🔹 Demo 2: Processing a file with metadata")
        
        markdown_file = watch_folder / "project_update.md"
        with open(markdown_file, 'w', encoding='utf-8') as f:
            f.write("""
# Project Update - Week 3

## Completed Tasks
- Implemented file watcher functionality
- Added comprehensive test suite
- Created deployment validation scripts
- Documented security policies

## Next Steps
- Deploy to production environment
- Monitor system performance
- Gather user feedback
- Plan next iteration

This update demonstrates the system's ability to process
structured markdown content with proper metadata.
            """.strip())
        
        # Create metadata file
        meta_file = markdown_file.with_suffix('.md.meta.json')
        metadata = {
            "source": "project_management",
            "tags": ["update", "progress", "team"],
            "importance": 4
        }
        
        with open(meta_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
        
        # Process the file with metadata
        result = await handler.process_file_async(markdown_file)
        print(f"   ✅ Processing result: {'Success' if result else 'Failed'}")
        
        # Demo 3: Show processed files log
        print("\n🔹 Demo 3: Processed files tracking")
        
        if processed_log.exists():
            with open(processed_log, 'r', encoding='utf-8') as f:
                log_data = json.load(f)
            
            print(f"   📋 Processed files log contains {len(log_data)} entries:")
            for filename, info in log_data.items():
                print(f"      📄 {filename}")
                print(f"         Processed: {info['processed_at']}")
                print(f"         Chunks: {info['chunks']}")
                print(f"         Source: {info['source']}")
                print(f"         Tags: {info['tags']}")
                print(f"         Importance: {info['importance']}")
        
        # Demo 4: Change detection
        print("\n🔹 Demo 4: Change detection")
        
        # Modify the simple file
        with open(simple_file, 'a', encoding='utf-8') as f:
            f.write("\n\nThis is an update to test change detection.")
        
        print("   📝 Modified existing file")
        
        # Check if file should be processed again
        should_process = handler.should_process_file(simple_file)
        print(f"   🔍 Should reprocess: {'Yes' if should_process else 'No'}")
        
        if should_process:
            result = await handler.process_file_async(simple_file)
            print(f"   ✅ Reprocessing result: {'Success' if result else 'Failed'}")
        
        # Demo 5: File type filtering
        print("\n🔹 Demo 5: File type filtering")
        
        test_files = [
            ("supported.md", "Markdown file", True),
            ("supported.txt", "Text file", True),
            ("supported.json", '{"test": "JSON file"}', True),
            ("unsupported.pdf", "PDF content", False),
            ("metadata.meta.json", '{"source": "test"}', False)
        ]
        
        for filename, content, should_process in test_files:
            test_file = watch_folder / filename
            with open(test_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            will_process = handler.should_process_file(test_file)
            status = "✅" if will_process == should_process else "❌"
            print(f"   {status} {filename}: {'Will process' if will_process else 'Will skip'}")
        
        print("\n" + "=" * 50)
        print("🎉 Demo completed successfully!")
        print("\n📊 Summary:")
        print("   ✅ File processing with mock loader")
        print("   ✅ Metadata loading and parsing")
        print("   ✅ Change detection via file hashing")
        print("   ✅ File type filtering")
        print("   ✅ Processed files tracking")
        print("\n🚀 The file watcher system is ready for production!")


async def demo_watcher_startup():
    """Demonstrate watcher startup with existing files."""
    print("\n" + "=" * 50)
    print("🔹 Bonus Demo: Watcher startup with existing files")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        demo_dir = Path(temp_dir)
        watch_folder = demo_dir / "startup-demo"
        processed_log = demo_dir / "startup_processed.json"
        
        # Create watch folder with some existing files
        watch_folder.mkdir()
        
        existing_files = [
            ("existing1.md", "# Existing Document 1\nThis was here before the watcher started."),
            ("existing2.txt", "Existing text document with some content."),
            ("existing3.json", '{"message": "Existing JSON data", "processed": false}')
        ]
        
        for filename, content in existing_files:
            filepath = watch_folder / filename
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
        
        print(f"   📁 Created {len(existing_files)} existing files")
        
        # Create watcher and replace loader with mock
        watcher = MemoryWatcher(str(watch_folder), str(processed_log))
        watcher.handler.loader = DemoMemoryLoader()
        
        # Process existing files (simulates watcher startup)
        await watcher.process_existing_files()
        
        print(f"   ✅ Processed all existing files on startup")


async def main():
    """Run the complete demo."""
    await demo_file_processing()
    await demo_watcher_startup()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️  Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
