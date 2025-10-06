#!/usr/bin/env python3
"""
Check Sparky Ingestion Progress
Utility to check the status of ongoing Sparky export ingestion.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path


def load_progress(progress_file: Path) -> dict:
    """Load progress data from file."""
    if not progress_file.exists():
        return {}
    
    try:
        with open(progress_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Error loading progress file: {e}")
        return {}


def print_progress_report(progress_data: dict) -> None:
    """Print a detailed progress report."""
    if not progress_data:
        print("📋 No progress file found - ingestion not started yet")
        return
    
    print(f"{'='*60}")
    print(f"📊 SPARKY INGESTION PROGRESS REPORT")
    print(f"{'='*60}")
    
    # Basic info
    last_updated = progress_data.get('last_updated')
    if last_updated:
        dt = datetime.fromisoformat(last_updated)
        print(f"🕐 Last updated: {dt.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Statistics
    stats = progress_data.get('stats', {})
    total_conversations = stats.get('total_conversations', 0)
    total_messages = stats.get('total_messages', 0)
    processed_messages = stats.get('processed_messages', 0)
    
    processed_conversations = len(progress_data.get('processed_conversations', []))
    
    print(f"\n📈 OVERALL PROGRESS:")
    print(f"📚 Total conversations: {total_conversations:,}")
    print(f"✅ Processed conversations: {processed_conversations:,}")
    
    if total_conversations > 0:
        conv_progress = (processed_conversations / total_conversations) * 100
        print(f"📊 Conversation progress: {conv_progress:.1f}%")
        remaining_conversations = total_conversations - processed_conversations
        print(f"⏳ Remaining conversations: {remaining_conversations:,}")
    
    print(f"\n💬 MESSAGE PROCESSING:")
    print(f"📝 Total messages found: {total_messages:,}")
    print(f"✅ Messages processed: {processed_messages:,}")
    
    if total_messages > 0:
        msg_progress = (processed_messages / total_messages) * 100
        print(f"📊 Message progress: {msg_progress:.1f}%")
    
    # Current session stats
    current_processed = stats.get('current_session_processed', 0)
    current_skipped = stats.get('current_session_skipped', 0)
    current_failed = stats.get('current_session_failed', 0)
    
    if current_processed > 0 or current_skipped > 0 or current_failed > 0:
        print(f"\n🔄 LAST SESSION:")
        print(f"✅ Processed: {current_processed:,}")
        print(f"⏭️  Skipped: {current_skipped:,}")
        print(f"❌ Failed: {current_failed:,}")
    
    print(f"\n{'='*60}")


def estimate_remaining_time(progress_data: dict) -> None:
    """Estimate remaining processing time."""
    stats = progress_data.get('stats', {})
    total_conversations = stats.get('total_conversations', 0)
    processed_conversations = len(progress_data.get('processed_conversations', []))
    
    if total_conversations == 0 or processed_conversations == 0:
        print("⏱️  Cannot estimate time - insufficient data")
        return
    
    remaining_conversations = total_conversations - processed_conversations
    if remaining_conversations <= 0:
        print("🎉 Ingestion complete!")
        return
    
    # Rough estimates based on typical processing rates
    # These are conservative estimates
    avg_messages_per_conv = 25  # From your analysis
    seconds_per_message = 3     # Including API calls and delays
    
    estimated_messages = remaining_conversations * avg_messages_per_conv
    estimated_seconds = estimated_messages * seconds_per_message
    
    hours = estimated_seconds // 3600
    minutes = (estimated_seconds % 3600) // 60
    
    print(f"⏱️  ESTIMATED REMAINING TIME:")
    print(f"📊 Remaining conversations: {remaining_conversations:,}")
    print(f"📝 Estimated remaining messages: {estimated_messages:,}")
    
    if hours > 0:
        print(f"⏰ Estimated time: ~{hours}h {minutes}m")
    else:
        print(f"⏰ Estimated time: ~{minutes}m")
    
    print(f"💡 Note: This is a rough estimate. Actual time may vary based on:")
    print(f"   • API rate limits and response times")
    print(f"   • Message complexity and length")
    print(f"   • Network conditions")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Check Sparky ingestion progress'
    )
    parser.add_argument(
        '--progress-file',
        type=Path,
        default=Path('sparky_ingestion_progress.json'),
        help='Progress file location'
    )
    parser.add_argument(
        '--estimate-time',
        action='store_true',
        help='Show estimated remaining time'
    )
    parser.add_argument(
        '--reset',
        action='store_true',
        help='Delete progress file to start fresh'
    )
    
    args = parser.parse_args()
    
    if args.reset:
        if args.progress_file.exists():
            args.progress_file.unlink()
            print(f"🗑️  Deleted progress file: {args.progress_file}")
        else:
            print(f"📋 Progress file not found: {args.progress_file}")
        return
    
    try:
        progress_data = load_progress(args.progress_file)
        print_progress_report(progress_data)
        
        if args.estimate_time:
            print()
            estimate_remaining_time(progress_data)
        
        # Show resume command if needed
        if progress_data and progress_data.get('stats', {}).get('total_conversations', 0) > 0:
            processed_conversations = len(progress_data.get('processed_conversations', []))
            total_conversations = progress_data.get('stats', {}).get('total_conversations', 0)
            
            if processed_conversations < total_conversations:
                print(f"\n🔄 To resume ingestion:")
                print(f"   python ingest_sparky_export.py chat-history")
                print(f"\n🗑️  To start fresh:")
                print(f"   python ingest_sparky_export.py chat-history --reset")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
