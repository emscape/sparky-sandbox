#!/usr/bin/env python3
"""Test script for batch memory loading functionality."""

import asyncio
import tempfile
import os
from pathlib import Path

from load_memory_batch import BatchMemoryLoader


async def test_batch_loading():
    """Test the batch loading functionality with sample content."""
    print("🧪 Testing Batch Memory Loading")
    print("=" * 50)
    
    # Create test content
    test_content = """
# Test Document

This is a test document for the batch loading system.

## Section 1: Introduction

The AI memory system supports structured metadata including type, tags, source, and importance levels.
Each memory entry is associated with a user through Row Level Security policies.

## Section 2: Features

Key features include:
- Semantic search using vector embeddings
- Intelligent text chunking for large documents
- Async processing with retry logic
- Support for multiple file formats

## Section 3: Usage

Users can inject memories individually or in batches from files.
The system automatically handles tokenization and embedding generation.

This content should be split into multiple chunks based on the ~500 token limit.
Each chunk will be processed separately and stored in the database.
"""
    
    # Create temporary test file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
        f.write(test_content)
        temp_file = f.name
    
    try:
        print(f"📁 Created test file: {temp_file}")
        
        # Initialize loader
        loader = BatchMemoryLoader()
        
        # Test text chunking
        print("\n🔪 Testing text chunking...")
        chunks = loader.chunk_text(test_content)
        print(f"Split into {len(chunks)} chunks:")
        
        for i, chunk in enumerate(chunks, 1):
            token_count = loader.count_tokens(chunk)
            print(f"  Chunk {i}: {len(chunk)} chars, ~{token_count} tokens")
            print(f"    Preview: {chunk[:100]}...")
        
        # Test source detection
        print(f"\n🏷️  Testing source detection...")
        detected_source = loader.detect_source_from_filename(temp_file)
        print(f"Detected source: {detected_source}")
        
        # Test file reading
        print(f"\n📄 Testing file reading...")
        content = loader.read_file_content(temp_file)
        print(f"Read {len(content)} characters")
        
        print("\n✅ All tests passed!")
        print("Note: To test full database integration, run:")
        print(f"python load_memory_batch.py {temp_file} --tags='test,batch' --importance=1")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
    finally:
        # Clean up
        if os.path.exists(temp_file):
            os.unlink(temp_file)
            print(f"🗑️  Cleaned up test file")


if __name__ == "__main__":
    asyncio.run(test_batch_loading())
