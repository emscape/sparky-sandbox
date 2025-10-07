#!/usr/bin/env python3
"""Batch memory loading utilities for AI Memory System."""

import argparse
import asyncio
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, AsyncGenerator
import tiktoken
from openai import AsyncOpenAI
from supabase import create_client, Client

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.memory.utils import get_embedding
from config import config, parse_tags, validate_importance


class BatchMemoryLoader:
    """Handles batch loading of memories from files."""

    def __init__(self, project_id: Optional[str] = None, summarize: bool = False) -> None:
        """Initialize OpenAI and Supabase clients."""
        self.openai_client = AsyncOpenAI(api_key=config.openai_api_key)
        self.supabase: Client = create_client(config.supabase_url, config.supabase_key)
        self.tokenizer = tiktoken.get_encoding("cl100k_base")  # GPT-4 tokenizer
        self.project_id = project_id
        self.summarize = summarize
        
        # Statistics
        self.total_chunks = 0
        self.successful_inserts = 0
        self.failed_inserts = 0
        self.skipped_chunks = 0
        self.summarized_chunks = 0

    async def summarize_chunk(self, chunk: str) -> str:
        """Summarize a chunk to reduce cost and noise."""
        if not self.summarize or len(chunk) < 200:
            return chunk
        
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",  # Use cheaper model for summarization
                messages=[
                    {
                        "role": "system", 
                        "content": "Summarize the following text concisely, preserving key information and context. Keep it under 150 words."
                    },
                    {"role": "user", "content": chunk}
                ],
                max_tokens=200,
                temperature=0.3
            )
            
            summary = response.choices[0].message.content.strip()
            if summary:
                self.summarized_chunks += 1
                return summary
            else:
                return chunk
                
        except Exception as e:
            print(f"⚠️  Summarization failed, using original text: {e}")
            return chunk

    def count_tokens(self, text: str) -> int:
        """Count tokens in text using tiktoken."""
        return len(self.tokenizer.encode(text))

    def detect_source_from_filename(self, filepath: str) -> str:
        """Auto-detect source type from filename patterns."""
        filename = Path(filepath).stem.lower()
        
        # Common patterns
        if any(word in filename for word in ['chat', 'conversation', 'messages']):
            return 'chat'
        elif any(word in filename for word in ['blog', 'post', 'article']):
            return 'blog'
        elif any(word in filename for word in ['email', 'mail']):
            return 'email'
        elif any(word in filename for word in ['doc', 'documentation', 'readme']):
            return 'documentation'
        elif any(word in filename for word in ['log', 'logs']):
            return 'log'
        elif any(word in filename for word in ['note', 'notes']):
            return 'notes'
        else:
            return 'file'

    def read_file_content(self, filepath: str) -> str:
        """Read and return file content based on extension."""
        path = Path(filepath)
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {filepath}")
        
        try:
            if path.suffix.lower() == '.json':
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                # Convert JSON to readable text
                if isinstance(data, dict):
                    return json.dumps(data, indent=2)
                elif isinstance(data, list):
                    return '\n'.join(str(item) for item in data)
                else:
                    return str(data)
            else:
                # Handle .txt, .md, and other text files
                with open(path, 'r', encoding='utf-8') as f:
                    return f.read()
        except UnicodeDecodeError:
            # Try with different encoding
            with open(path, 'r', encoding='latin-1') as f:
                return f.read()
        except Exception as e:
            raise RuntimeError(f"Failed to read file {filepath}: {e}")

    def clean_text(self, text: str) -> str:
        """Clean and normalize text content."""
        # Remove excessive whitespace
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        # Remove trailing whitespace from lines
        text = '\n'.join(line.rstrip() for line in text.split('\n'))
        # Remove excessive spaces
        text = re.sub(r' +', ' ', text)
        return text.strip()

    def chunk_text(self, text: str, max_tokens: int = 500, overlap_tokens: int = 50) -> List[str]:
        """Split text into chunks of approximately max_tokens each with overlap."""
        if not text.strip():
            return []
        
        # Clean the text first
        text = self.clean_text(text)
        
        # If text is short enough, return as single chunk
        if self.count_tokens(text) <= max_tokens:
            return [text] if text.strip() else []
        
        chunks = []
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        current_chunk = ""
        current_tokens = 0
        
        for sentence in sentences:
            sentence_tokens = self.count_tokens(sentence)
            
            # If single sentence is too long, split it further
            if sentence_tokens > max_tokens:
                # Save current chunk if it has content
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
                    current_tokens = 0
                
                # Split long sentence by words
                words = sentence.split()
                temp_chunk = ""
                temp_tokens = 0
                
                for word in words:
                    word_tokens = self.count_tokens(word + " ")
                    if temp_tokens + word_tokens > max_tokens and temp_chunk:
                        chunks.append(temp_chunk.strip())
                        temp_chunk = word + " "
                        temp_tokens = word_tokens
                    else:
                        temp_chunk += word + " "
                        temp_tokens += word_tokens
                
                if temp_chunk.strip():
                    current_chunk = temp_chunk
                    current_tokens = temp_tokens
            
            # Normal sentence processing
            elif current_tokens + sentence_tokens > max_tokens:
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + " "
                current_tokens = sentence_tokens
            else:
                current_chunk += sentence + " "
                current_tokens += sentence_tokens
        
        # Add final chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        # Filter out empty or very short chunks
        valid_chunks = []
        for chunk in chunks:
            if chunk.strip() and len(chunk.strip()) > 10:  # Minimum 10 characters
                valid_chunks.append(chunk.strip())
        
        return valid_chunks

    async def store_chunk_with_retry(self, chunk: str, metadata: Dict[str, Any], 
                                   max_retries: int = 3) -> Optional[Dict[str, Any]]:
        """Store a single chunk with retry logic."""
        for attempt in range(max_retries):
            try:
                # Apply summarization if enabled
                processed_chunk = await self.summarize_chunk(chunk)
                
                # Generate embedding
                embedding = await get_embedding(processed_chunk, self.openai_client)
                
                # Prepare data
                data = {
                    "content": processed_chunk,
                    "embedding": embedding,
                    "type": metadata["type"],
                    "source": metadata["source"],
                    "importance": metadata["importance"]
                }
                
                # Add project_id if specified
                if self.project_id:
                    data["project_id"] = self.project_id
                
                if metadata.get("tags"):
                    data["tags"] = metadata["tags"]
                
                # Insert into database
                result = self.supabase.table(config.memory_table).insert(data).execute()
                
                if result.data:
                    return result.data[0]
                else:
                    raise RuntimeError("No data returned from insert operation")
                    
            except Exception as e:
                if attempt == max_retries - 1:
                    print(f"❌ Failed to store chunk after {max_retries} attempts: {e}")
                    return None
                else:
                    print(f"⚠️  Attempt {attempt + 1} failed, retrying: {e}")
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
        
        return None

    async def process_file(self, filepath: str, source: Optional[str] = None,
                          tags: Optional[List[str]] = None, importance: int = 1) -> None:
        """Process a single file and load all chunks into memory."""
        print(f"📁 Processing file: {filepath}")
        
        try:
            # Read file content
            content = self.read_file_content(filepath)
            print(f"📄 File size: {len(content)} characters")
            
            # Detect source if not provided
            if not source:
                source = self.detect_source_from_filename(filepath)
            
            # Chunk the content
            chunks = self.chunk_text(content)
            print(f"🔪 Split into {len(chunks)} chunks")
            
            if not chunks:
                print("⚠️  No valid chunks found, skipping file")
                return
            
            # Prepare metadata
            metadata = {
                "type": "log",
                "source": source,
                "tags": tags,
                "importance": importance
            }
            
            # Process chunks with progress tracking
            print(f"🚀 Processing {len(chunks)} chunks...")
            
            # Process chunks in batches to avoid overwhelming the API
            batch_size = 5
            for i in range(0, len(chunks), batch_size):
                batch = chunks[i:i + batch_size]
                tasks = []
                
                for j, chunk in enumerate(batch):
                    self.total_chunks += 1
                    chunk_num = i + j + 1
                    print(f"  📝 Processing chunk {chunk_num}/{len(chunks)} ({len(chunk)} chars, ~{self.count_tokens(chunk)} tokens)")
                    
                    if not chunk.strip():
                        self.skipped_chunks += 1
                        continue
                    
                    task = self.store_chunk_with_retry(chunk, metadata)
                    tasks.append(task)
                
                # Wait for batch to complete
                if tasks:
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    for result in results:
                        if isinstance(result, Exception):
                            self.failed_inserts += 1
                        elif result is not None:
                            self.successful_inserts += 1
                        else:
                            self.failed_inserts += 1
                
                # Small delay between batches
                if i + batch_size < len(chunks):
                    await asyncio.sleep(1)
            
            print(f"✅ Completed processing {filepath}")
            
        except Exception as e:
            print(f"❌ Error processing file {filepath}: {e}")

    def print_summary(self) -> None:
        """Print processing summary."""
        print("\n" + "=" * 60)
        print("📊 BATCH PROCESSING SUMMARY")
        print("=" * 60)
        print(f"Total chunks processed: {self.total_chunks}")
        print(f"Successfully stored: {self.successful_inserts}")
        print(f"Failed to store: {self.failed_inserts}")
        print(f"Skipped (empty): {self.skipped_chunks}")
        
        if self.summarize:
            print(f"Summarized chunks: {self.summarized_chunks}")
        
        if self.project_id:
            print(f"Project ID: {self.project_id}")
        
        if self.total_chunks > 0:
            success_rate = (self.successful_inserts / self.total_chunks) * 100
            print(f"Success rate: {success_rate:.1f}%")
        
        print("=" * 60)


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Batch load memories from text files into AI memory system',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python load_memory_batch.py chat.md --source=chat --tags="sparky,emstyle" --importance=2
  python load_memory_batch.py document.txt --tags="project,notes"
  python load_memory_batch.py data.json --source=api --importance=3
        """
    )
    
    parser.add_argument('filepath', help='Path to the file to process (.txt, .md, or .json)')
    parser.add_argument('--source', help='Memory source (auto-detected from filename if not provided)')
    parser.add_argument('--tags', help='Comma-separated tags (e.g., "sparky,emstyle")')
    parser.add_argument('--importance', type=int, default=1, 
                       help='Importance level (1=low to 5=critical, default: 1)')
    
    return parser.parse_args()


async def main() -> None:
    """Main function to handle batch processing."""
    try:
        args = parse_arguments()
        
        # Validate arguments
        if not os.path.exists(args.filepath):
            print(f"❌ Error: File not found: {args.filepath}")
            sys.exit(1)
        
        # Check file extension
        allowed_extensions = {'.txt', '.md', '.json'}
        file_ext = Path(args.filepath).suffix.lower()
        if file_ext not in allowed_extensions:
            print(f"❌ Error: Unsupported file type: {file_ext}")
            print(f"Supported types: {', '.join(allowed_extensions)}")
            sys.exit(1)
        
        # Validate importance
        importance = validate_importance(args.importance)
        
        # Parse tags
        tags = parse_tags(args.tags) if args.tags else None
        
        # Initialize loader with new options
        loader = BatchMemoryLoader(
            project_id=args.project_id,
            summarize=args.summarize
        )
        
        # Process file
        start_time = time.time()
        await loader.process_file(
            filepath=args.filepath,
            source=args.source,
            tags=tags,
            importance=importance
        )
        
        # Print summary
        end_time = time.time()
        processing_time = end_time - start_time
        
        loader.print_summary()
        print(f"⏱️  Total processing time: {processing_time:.2f} seconds")
        
        if loader.failed_inserts > 0:
            sys.exit(1)  # Exit with error code if there were failures
            
    except KeyboardInterrupt:
        print("\n⏹️  Processing interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
