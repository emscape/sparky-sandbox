#!/usr/bin/env python3
"""
Sparky Chat History Ingestion Script
Processes ChatGPT/Sparky web export data for the AI memory system.
"""

import argparse
import asyncio
import json
import os
import re
import sys
import time
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass

from openai import AsyncOpenAI
from supabase import create_client, Client
from config import config, parse_tags, validate_importance
from utils import get_embedding


@dataclass
class ConversationMessage:
    """Structured representation of a conversation message."""
    id: str
    role: str  # 'user', 'assistant', 'system'
    content: str
    create_time: Optional[float]
    conversation_id: str
    conversation_title: str
    parent_id: Optional[str] = None
    metadata: Optional[Dict] = None


class SparkyExportProcessor:
    """Processes Sparky/ChatGPT export data for memory ingestion."""

    def __init__(self, progress_file: Optional[Path] = None):
        """Initialize the processor with API clients."""
        self.openai_client = AsyncOpenAI(api_key=config.openai_api_key)
        self.supabase: Client = create_client(config.supabase_url, config.supabase_key)

        # Progress tracking
        self.progress_file = progress_file or Path('sparky_ingestion_progress.json')
        self.processed_conversations = set()
        self.processed_messages = set()
        self.load_progress()

        # Processing statistics
        self.total_conversations = 0
        self.total_messages = 0
        self.current_processed_messages = 0
        self.current_skipped_messages = 0
        self.current_failed_inserts = 0

        # Content filters
        self.skip_roles = {'system'}  # Skip system messages by default
        self.skip_content_types = {'user_editable_context', 'thoughts', 'reasoning_recap'}
        self.min_content_length = 10  # Skip very short messages

    def generate_content_hash(self, content: str) -> str:
        """Generate a hash for content to detect duplicates."""
        return hashlib.md5(content.encode('utf-8')).hexdigest()

    def load_progress(self) -> None:
        """Load progress from previous runs."""
        if self.progress_file.exists():
            try:
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    progress_data = json.load(f)

                self.processed_conversations = set(progress_data.get('processed_conversations', []))
                self.processed_messages = set(progress_data.get('processed_messages', []))

                print(f"📋 Loaded progress: {len(self.processed_conversations)} conversations, "
                      f"{len(self.processed_messages)} messages already processed")

            except Exception as e:
                print(f"⚠️  Could not load progress file: {e}")
                self.processed_conversations = set()
                self.processed_messages = set()
        else:
            print("🆕 Starting fresh ingestion (no progress file found)")

    def save_progress(self) -> None:
        """Save current progress to file."""
        try:
            progress_data = {
                'processed_conversations': list(self.processed_conversations),
                'processed_messages': list(self.processed_messages),
                'last_updated': datetime.now().isoformat(),
                'stats': {
                    'total_conversations': self.total_conversations,
                    'total_messages': self.total_messages,
                    'processed_messages': len(self.processed_messages),
                    'current_session_processed': self.current_processed_messages,
                    'current_session_skipped': self.current_skipped_messages,
                    'current_session_failed': self.current_failed_inserts
                }
            }

            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(progress_data, f, indent=2)

        except Exception as e:
            print(f"⚠️  Could not save progress: {e}")

    def is_conversation_processed(self, conversation_id: str) -> bool:
        """Check if a conversation has already been processed."""
        return conversation_id in self.processed_conversations

    def is_message_processed(self, message_hash: str) -> bool:
        """Check if a message has already been processed."""
        return message_hash in self.processed_messages

    def mark_conversation_processed(self, conversation_id: str) -> None:
        """Mark a conversation as processed."""
        self.processed_conversations.add(conversation_id)
        self.save_progress()

    def mark_message_processed(self, message_hash: str) -> None:
        """Mark a message as processed."""
        self.processed_messages.add(message_hash)

    def load_conversations(self, conversations_file: Path) -> List[Dict]:
        """Load conversations from the JSON export file."""
        try:
            with open(conversations_file, 'r', encoding='utf-8') as f:
                conversations = json.load(f)
            print(f"📚 Loaded {len(conversations)} conversations from {conversations_file}")
            return conversations
        except Exception as e:
            print(f"❌ Error loading conversations: {e}")
            return []
    
    def extract_messages_from_conversation(self, conversation: Dict) -> List[ConversationMessage]:
        """Extract meaningful messages from a conversation tree."""
        messages = []
        mapping = conversation.get('mapping', {})
        title = conversation.get('title', 'Untitled Conversation')
        conv_id = conversation.get('conversation_id', 'unknown')
        
        for node_id, node in mapping.items():
            message_data = node.get('message')
            if not message_data:
                continue
                
            # Extract basic message info
            author = message_data.get('author', {})
            role = author.get('role', 'unknown')
            content_data = message_data.get('content', {})
            content_type = content_data.get('content_type', 'text')
            
            # Skip unwanted content types and roles
            if role in self.skip_roles or content_type in self.skip_content_types:
                continue
                
            # Extract text content
            parts = content_data.get('parts', [])
            if not parts:
                continue
                
            # Join all text parts
            content = '\n'.join(str(part) for part in parts if part)
            content = content.strip()
            
            # Skip empty or very short content
            if len(content) < self.min_content_length:
                continue
                
            # Create message object
            message = ConversationMessage(
                id=message_data.get('id', node_id),
                role=role,
                content=content,
                create_time=message_data.get('create_time'),
                conversation_id=conv_id,
                conversation_title=title,
                parent_id=node.get('parent'),
                metadata={
                    'content_type': content_type,
                    'status': message_data.get('status'),
                    'model_slug': message_data.get('metadata', {}).get('model_slug'),
                    'request_id': message_data.get('metadata', {}).get('request_id')
                }
            )
            
            messages.append(message)
            
        return messages
    
    def determine_message_importance(self, message: ConversationMessage) -> int:
        """Determine importance level (1-5) based on message content and context."""
        content = message.content.lower()
        
        # High importance indicators
        if any(keyword in content for keyword in [
            'error', 'problem', 'issue', 'bug', 'fix', 'solution',
            'important', 'critical', 'urgent', 'help', 'stuck'
        ]):
            return 4
            
        # Medium-high importance for technical content
        if any(keyword in content for keyword in [
            'code', 'function', 'class', 'api', 'database', 'server',
            'algorithm', 'implementation', 'architecture', 'design'
        ]):
            return 3
            
        # Medium importance for learning/discussion
        if any(keyword in content for keyword in [
            'learn', 'understand', 'explain', 'how', 'why', 'what',
            'tutorial', 'guide', 'example', 'documentation'
        ]):
            return 3
            
        # Lower importance for casual conversation
        if len(message.content) < 50:
            return 1
            
        return 2  # Default importance
    
    def generate_message_tags(self, message: ConversationMessage) -> List[str]:
        """Generate relevant tags for a message based on content and context."""
        tags = ['sparky-export', 'chat-history']
        content = message.content.lower()
        
        # Add role-based tag
        tags.append(f"role-{message.role}")
        
        # Technical tags
        tech_keywords = {
            'python': ['python', 'py', 'pip', 'django', 'flask'],
            'javascript': ['javascript', 'js', 'node', 'npm', 'react'],
            'web': ['html', 'css', 'website', 'browser', 'frontend'],
            'database': ['database', 'sql', 'supabase', 'postgres'],
            'ai': ['ai', 'gpt', 'openai', 'model', 'embedding', 'llm'],
            'coding': ['code', 'function', 'class', 'variable', 'algorithm']
        }
        
        for tag, keywords in tech_keywords.items():
            if any(keyword in content for keyword in keywords):
                tags.append(tag)
        
        # Project-specific tags
        if any(keyword in content for keyword in ['stellarus', 'innovation', 'engineer']):
            tags.append('stellarus')
            
        if any(keyword in content for keyword in ['girls who code', 'gwc', 'students']):
            tags.append('education')
            
        # Conversation context
        if 'error' in content or 'problem' in content:
            tags.append('troubleshooting')
            
        if any(keyword in content for keyword in ['tutorial', 'guide', 'how to']):
            tags.append('tutorial')
            
        return tags

    async def store_message_with_retry(self, message: ConversationMessage,
                                     tags: List[str], importance: int,
                                     max_retries: int = 3) -> bool:
        """Store a message in the database with retry logic."""
        # Generate content hash for deduplication
        content_hash = self.generate_content_hash(message.content)

        # Check if already processed
        if self.is_message_processed(content_hash):
            print(f"  ⏭️  Message already processed, skipping")
            return True

        for attempt in range(max_retries):
            try:
                # Generate embedding
                print(f"      🔄 Generating embedding...")
                embedding = await get_embedding(message.content, self.openai_client)
                print(f"      ✅ Embedding generated ({len(embedding)} dimensions)")

                # Prepare data for insertion
                data = {
                    "content": message.content,
                    "embedding": embedding,
                    "type": "chat",
                    "source": "sparky-export",
                    "importance": importance,
                    "tags": tags,
                    "metadata": {
                        "conversation_id": message.conversation_id,
                        "conversation_title": message.conversation_title,
                        "message_id": message.id,
                        "role": message.role,
                        "create_time": message.create_time,
                        "parent_id": message.parent_id,
                        "content_hash": content_hash,
                        **message.metadata
                    }
                }

                # Insert into database
                print(f"      💾 Inserting into database...")
                result = self.supabase.table(config.memory_table).insert(data).execute()

                if result.data:
                    # Mark as processed
                    self.mark_message_processed(content_hash)
                    print(f"      ✅ Successfully stored!")
                    return True
                else:
                    raise RuntimeError("No data returned from insert")

            except Exception as e:
                error_msg = str(e)
                print(f"\n  ❌ ERROR on attempt {attempt + 1}/{max_retries}:")
                print(f"     Error type: {type(e).__name__}")
                print(f"     Error message: {error_msg[:200]}")

                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    print(f"     ⏳ Waiting {wait_time}s before retry...")
                    await asyncio.sleep(wait_time)
                else:
                    print(f"\n  🛑 FAILED after {max_retries} attempts")
                    print(f"     Message content preview: {message.content[:100]}...")
                    print(f"     Pausing for 5 seconds so you can see this error...")
                    await asyncio.sleep(5)
                    return False

        return False

    async def process_conversation(self, conversation: Dict) -> None:
        """Process a single conversation and store its messages."""
        title = conversation.get('title', 'Untitled')
        conv_id = conversation.get('conversation_id', 'unknown')

        # Check if conversation already processed
        if self.is_conversation_processed(conv_id):
            print(f"\n⏭️  Conversation already processed: '{title}' ({conv_id})")
            return

        print(f"\n📖 Processing: '{title}' ({conv_id})")

        # Extract messages
        messages = self.extract_messages_from_conversation(conversation)
        self.total_messages += len(messages)

        if not messages:
            print("  ⚠️  No meaningful messages found, skipping")
            self.current_skipped_messages += len(messages)
            # Still mark as processed to avoid re-checking
            self.mark_conversation_processed(conv_id)
            return

        print(f"  📝 Found {len(messages)} meaningful messages")

        # Process messages in batches
        batch_size = 3  # Small batches to avoid rate limits
        conversation_success = True

        for i in range(0, len(messages), batch_size):
            batch = messages[i:i + batch_size]
            tasks = []

            for j, message in enumerate(batch):
                msg_num = i + j + 1
                print(f"    💬 Processing message {msg_num}/{len(messages)} ({message.role})")

                # Generate tags and importance
                tags = self.generate_message_tags(message)
                importance = self.determine_message_importance(message)

                # Create storage task
                task = self.store_message_with_retry(message, tags, importance)
                tasks.append(task)

            # Execute batch
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)

                for result in results:
                    if isinstance(result, Exception):
                        self.current_failed_inserts += 1
                        conversation_success = False
                    elif result:
                        self.current_processed_messages += 1
                    else:
                        self.current_failed_inserts += 1
                        conversation_success = False

                # Save progress periodically (every batch)
                if i % (batch_size * 5) == 0:  # Every 5 batches
                    self.save_progress()

                # Small delay between batches
                await asyncio.sleep(1)

        # Mark conversation as processed if successful
        if conversation_success:
            self.mark_conversation_processed(conv_id)
            print(f"  ✅ Conversation completed successfully")
        else:
            print(f"  ⚠️  Conversation completed with some failures")

    async def process_export_folder(self, export_folder: Path) -> None:
        """Process the entire Sparky export folder."""
        conversations_file = export_folder / 'conversations.json'

        if not conversations_file.exists():
            print(f"❌ conversations.json not found in {export_folder}")
            return

        print(f"🚀 Processing Sparky export from: {export_folder}")
        print(f"📁 Progress file: {self.progress_file}")

        # Load conversations
        conversations = self.load_conversations(conversations_file)
        if not conversations:
            return

        self.total_conversations = len(conversations)

        # Filter out already processed conversations
        remaining_conversations = [
            conv for conv in conversations
            if not self.is_conversation_processed(conv.get('conversation_id', 'unknown'))
        ]

        if len(remaining_conversations) < len(conversations):
            already_processed = len(conversations) - len(remaining_conversations)
            print(f"📋 Resuming: {already_processed} conversations already processed, "
                  f"{len(remaining_conversations)} remaining")

        if not remaining_conversations:
            print("✅ All conversations already processed!")
            self.print_summary()
            return

        # Process each remaining conversation
        for i, conversation in enumerate(remaining_conversations, 1):
            total_progress = len(conversations) - len(remaining_conversations) + i
            print(f"\n📊 Progress: {total_progress}/{len(conversations)} conversations "
                  f"(Session: {i}/{len(remaining_conversations)})")

            try:
                await self.process_conversation(conversation)
            except KeyboardInterrupt:
                print(f"\n⏸️  Interrupted! Progress saved. Resume with the same command.")
                self.save_progress()
                raise
            except Exception as e:
                print(f"❌ Error processing conversation: {e}")
                # Continue with next conversation
                continue

        # Final save and summary
        self.save_progress()
        self.print_summary()

    def print_summary(self) -> None:
        """Print processing summary."""
        print(f"\n{'='*70}")
        print(f"📊 SPARKY EXPORT PROCESSING SUMMARY")
        print(f"{'='*70}")

        # Overall statistics
        print(f"📚 Total conversations in export: {self.total_conversations}")
        print(f"✅ Conversations processed (all time): {len(self.processed_conversations)}")
        print(f"💬 Messages processed (all time): {len(self.processed_messages)}")

        # Current session statistics
        print(f"\n🔄 CURRENT SESSION:")
        print(f"✅ Messages processed: {self.current_processed_messages}")
        print(f"⏭️  Messages skipped: {self.current_skipped_messages}")
        print(f"❌ Failed inserts: {self.current_failed_inserts}")

        # Calculate rates
        total_current = (self.current_processed_messages +
                        self.current_skipped_messages +
                        self.current_failed_inserts)

        if total_current > 0:
            success_rate = (self.current_processed_messages / total_current) * 100
            print(f"📈 Session success rate: {success_rate:.1f}%")

        # Progress information
        remaining_conversations = self.total_conversations - len(self.processed_conversations)
        if remaining_conversations > 0:
            print(f"\n⏳ REMAINING WORK:")
            print(f"📋 Conversations remaining: {remaining_conversations}")
            print(f"💾 Progress saved to: {self.progress_file}")
            print(f"🔄 Resume with: python ingest_sparky_export.py chat-history")
        else:
            print(f"\n🎉 INGESTION COMPLETE!")
            print(f"🗑️  You can delete: {self.progress_file}")

        print(f"{'='*70}")


async def main():
    """Main function to handle command line execution."""
    parser = argparse.ArgumentParser(
        description='Ingest Sparky/ChatGPT export data into AI memory system'
    )
    parser.add_argument(
        'export_folder',
        help='Path to the chat-history export folder'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Parse and analyze without storing in database'
    )
    parser.add_argument(
        '--progress-file',
        type=Path,
        help='Custom progress file location (default: sparky_ingestion_progress.json)'
    )
    parser.add_argument(
        '--reset',
        action='store_true',
        help='Reset progress and start fresh (deletes progress file)'
    )

    args = parser.parse_args()

    export_path = Path(args.export_folder)
    if not export_path.exists():
        print(f"❌ Export folder not found: {export_path}")
        sys.exit(1)

    if not export_path.is_dir():
        print(f"❌ Path is not a directory: {export_path}")
        sys.exit(1)

    try:
        # Handle reset option
        progress_file = args.progress_file or Path('sparky_ingestion_progress.json')
        if args.reset and progress_file.exists():
            progress_file.unlink()
            print(f"🗑️  Deleted progress file: {progress_file}")

        processor = SparkyExportProcessor(progress_file)

        if args.dry_run:
            print("🔍 DRY RUN MODE - No data will be stored")
            # TODO: Implement dry run analysis

        start_time = time.time()
        await processor.process_export_folder(export_path)
        end_time = time.time()

        processing_time = end_time - start_time
        print(f"⏱️  Session processing time: {processing_time:.2f} seconds")

        if processor.current_failed_inserts > 0:
            print(f"⚠️  Session completed with {processor.current_failed_inserts} failures")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n⏹️  Processing interrupted by user")
        print("Progress has been saved. Run the same command to resume.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {type(e).__name__}")
        print(f"   Message: {str(e)[:500]}")
        print(f"\n   Full traceback:")
        import traceback
        traceback.print_exc()
        print(f"\n   Pausing for 10 seconds so you can read this...")
        time.sleep(10)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
