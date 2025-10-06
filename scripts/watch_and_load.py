#!/usr/bin/env python3
"""File monitoring script for automated memory ingestion."""

import argparse
import asyncio
import json
import os
import signal
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import hashlib

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from load_memory_batch import BatchMemoryLoader
from config import parse_tags, validate_importance


class MemoryFileHandler(FileSystemEventHandler):
    """Handles file system events for memory ingestion."""
    
    def __init__(self, watch_folder: str, processed_log: str):
        """Initialize the file handler."""
        self.watch_folder = Path(watch_folder)
        self.processed_log = Path(processed_log)
        self.supported_extensions = {'.txt', '.md', '.json'}
        self.processing_queue = asyncio.Queue()
        self.loader = BatchMemoryLoader()
        
        # Load processed files log
        self.processed_files = self.load_processed_log()
        
        print(f"👁️  Watching folder: {self.watch_folder}")
        print(f"📋 Processed log: {self.processed_log}")
        print(f"📁 Supported extensions: {', '.join(self.supported_extensions)}")
    
    def load_processed_log(self) -> Dict[str, Dict[str, Any]]:
        """Load the processed files log."""
        if self.processed_log.exists():
            try:
                with open(self.processed_log, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️  Warning: Could not load processed log: {e}")
                return {}
        return {}
    
    def save_processed_log(self) -> None:
        """Save the processed files log."""
        try:
            # Ensure directory exists
            self.processed_log.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.processed_log, 'w', encoding='utf-8') as f:
                json.dump(self.processed_files, f, indent=2, default=str)
        except Exception as e:
            print(f"❌ Error saving processed log: {e}")
    
    def get_file_hash(self, filepath: Path) -> str:
        """Get MD5 hash of file content for change detection."""
        try:
            with open(filepath, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception:
            return ""
    
    def should_process_file(self, filepath: Path) -> bool:
        """Check if file should be processed."""
        # Check extension
        if filepath.suffix.lower() not in self.supported_extensions:
            return False
        
        # Skip metadata files
        if filepath.name.endswith('.meta.json'):
            return False
        
        # Check if already processed
        file_key = str(filepath.relative_to(self.watch_folder))
        current_hash = self.get_file_hash(filepath)
        
        if file_key in self.processed_files:
            stored_hash = self.processed_files[file_key].get('hash', '')
            if stored_hash == current_hash:
                return False  # File unchanged
        
        return True
    
    def load_metadata(self, filepath: Path) -> Dict[str, Any]:
        """Load metadata from .meta.json file if it exists."""
        meta_file = filepath.with_suffix(filepath.suffix + '.meta.json')
        
        # Default metadata
        metadata = {
            'source': 'manual',
            'tags': [],
            'importance': 1
        }
        
        if meta_file.exists():
            try:
                with open(meta_file, 'r', encoding='utf-8') as f:
                    meta_data = json.load(f)
                    
                # Update with loaded metadata
                if 'source' in meta_data:
                    metadata['source'] = meta_data['source']
                if 'tags' in meta_data:
                    if isinstance(meta_data['tags'], list):
                        metadata['tags'] = meta_data['tags']
                    elif isinstance(meta_data['tags'], str):
                        metadata['tags'] = parse_tags(meta_data['tags'])
                if 'importance' in meta_data:
                    try:
                        metadata['importance'] = validate_importance(int(meta_data['importance']))
                    except (ValueError, TypeError):
                        print(f"⚠️  Invalid importance in {meta_file}, using default")
                
                print(f"📋 Loaded metadata from {meta_file.name}")
                
            except Exception as e:
                print(f"⚠️  Warning: Could not load metadata from {meta_file}: {e}")
        
        return metadata
    
    def on_created(self, event):
        """Handle file creation events."""
        if not event.is_directory:
            self.queue_file_for_processing(Path(event.src_path))
    
    def on_modified(self, event):
        """Handle file modification events."""
        if not event.is_directory:
            self.queue_file_for_processing(Path(event.src_path))
    
    def queue_file_for_processing(self, filepath: Path):
        """Queue a file for processing."""
        if self.should_process_file(filepath):
            print(f"📥 Queuing file for processing: {filepath.name}")
            # Use asyncio.create_task to add to queue from sync context
            try:
                loop = asyncio.get_event_loop()
                loop.create_task(self.processing_queue.put(filepath))
            except RuntimeError:
                # If no event loop is running, we'll handle this in the main loop
                pass
    
    async def process_file_async(self, filepath: Path) -> bool:
        """Process a single file asynchronously."""
        try:
            print(f"\n🔄 Processing: {filepath.name}")
            
            # Load metadata
            metadata = self.load_metadata(filepath)
            
            # Reset loader statistics for this file
            self.loader.total_chunks = 0
            self.loader.successful_inserts = 0
            self.loader.failed_inserts = 0
            self.loader.skipped_chunks = 0
            
            # Process the file
            await self.loader.process_file(
                filepath=str(filepath),
                source=metadata['source'],
                tags=metadata['tags'] if metadata['tags'] else None,
                importance=metadata['importance']
            )
            
            # Update processed files log
            file_key = str(filepath.relative_to(self.watch_folder))
            self.processed_files[file_key] = {
                'processed_at': datetime.now().isoformat(),
                'hash': self.get_file_hash(filepath),
                'chunks': self.loader.successful_inserts,
                'source': metadata['source'],
                'tags': metadata['tags'],
                'importance': metadata['importance']
            }
            
            self.save_processed_log()
            
            print(f"✅ Successfully processed {filepath.name}")
            print(f"   Chunks stored: {self.loader.successful_inserts}")
            print(f"   Failed: {self.loader.failed_inserts}")
            
            return self.loader.failed_inserts == 0
            
        except Exception as e:
            print(f"❌ Error processing {filepath.name}: {e}")
            return False


class MemoryWatcher:
    """Main watcher class for automated memory ingestion."""
    
    def __init__(self, watch_folder: str = "memory-drops", 
                 processed_log: str = "processed_files.json"):
        """Initialize the memory watcher."""
        self.watch_folder = Path(watch_folder)
        self.processed_log = Path(processed_log)
        self.handler = MemoryFileHandler(str(self.watch_folder), str(self.processed_log))
        self.observer = Observer()
        self.running = False
        
        # Ensure watch folder exists
        self.watch_folder.mkdir(exist_ok=True)
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        print(f"\n🛑 Received signal {signum}, shutting down gracefully...")
        self.stop()
    
    def start(self):
        """Start watching for files."""
        print(f"🚀 Starting Memory Watcher")
        print(f"📁 Watch folder: {self.watch_folder.absolute()}")
        print(f"📋 Processed log: {self.processed_log.absolute()}")
        print("Press Ctrl+C to stop\n")
        
        # Setup file system observer
        self.observer.schedule(self.handler, str(self.watch_folder), recursive=False)
        self.observer.start()
        self.running = True
        
        # Process any existing files first
        asyncio.run(self.process_existing_files())
        
        # Start the main processing loop
        asyncio.run(self.processing_loop())
    
    def stop(self):
        """Stop the watcher."""
        self.running = False
        if self.observer.is_alive():
            self.observer.stop()
            self.observer.join()
        print("👋 Memory Watcher stopped")
    
    async def process_existing_files(self):
        """Process any existing files in the watch folder."""
        print("🔍 Checking for existing files...")
        
        existing_files = []
        for filepath in self.watch_folder.iterdir():
            if filepath.is_file() and self.handler.should_process_file(filepath):
                existing_files.append(filepath)
        
        if existing_files:
            print(f"📁 Found {len(existing_files)} existing files to process")
            for filepath in existing_files:
                await self.handler.process_file_async(filepath)
        else:
            print("📭 No existing files to process")
    
    async def processing_loop(self):
        """Main processing loop."""
        print("👁️  Watching for new files...\n")
        
        while self.running:
            try:
                # Check for queued files (with timeout to allow checking self.running)
                try:
                    filepath = await asyncio.wait_for(
                        self.handler.processing_queue.get(), 
                        timeout=1.0
                    )
                    await self.handler.process_file_async(filepath)
                except asyncio.TimeoutError:
                    # No files to process, continue loop
                    continue
                    
            except Exception as e:
                print(f"❌ Error in processing loop: {e}")
                await asyncio.sleep(1)


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Watch folder for files and automatically load them into memory system',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python watch_and_load.py                           # Watch default memory-drops/ folder
  python watch_and_load.py --folder /path/to/watch   # Watch custom folder
  python watch_and_load.py --daemon                  # Run as daemon process

Metadata files:
  Create a .meta.json file alongside your content file to specify metadata:
  
  example.md.meta.json:
  {
    "source": "chat",
    "tags": ["team", "meeting"],
    "importance": 3
  }
        """
    )
    
    parser.add_argument('--folder', default='memory-drops',
                       help='Folder to watch for files (default: memory-drops)')
    parser.add_argument('--log', default='processed_files.json',
                       help='Processed files log (default: processed_files.json)')
    parser.add_argument('--daemon', action='store_true',
                       help='Run as daemon process (suppress output)')
    
    return parser.parse_args()


def main():
    """Main function."""
    try:
        args = parse_arguments()
        
        # Create watcher
        watcher = MemoryWatcher(
            watch_folder=args.folder,
            processed_log=args.log
        )
        
        # Start watching
        watcher.start()
        
    except KeyboardInterrupt:
        print("\n⏹️  Interrupted by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
