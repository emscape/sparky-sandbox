#!/usr/bin/env python3
"""
Sparky Export Analysis Script
Analyzes ChatGPT/Sparky export data to understand content before ingestion.
"""

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Set


class SparkyExportAnalyzer:
    """Analyzes Sparky/ChatGPT export data structure and content."""
    
    def __init__(self):
        """Initialize the analyzer."""
        self.conversations = []
        self.stats = {
            'total_conversations': 0,
            'total_messages': 0,
            'messages_by_role': Counter(),
            'content_types': Counter(),
            'conversation_lengths': [],
            'topics': Counter(),
            'models_used': Counter(),
            'date_range': {'earliest': None, 'latest': None}
        }
    
    def load_conversations(self, conversations_file: Path) -> bool:
        """Load conversations from JSON file."""
        try:
            with open(conversations_file, 'r', encoding='utf-8') as f:
                self.conversations = json.load(f)
            print(f"✅ Loaded {len(self.conversations)} conversations")
            return True
        except Exception as e:
            print(f"❌ Error loading conversations: {e}")
            return False
    
    def analyze_conversation_structure(self, conversation: Dict) -> Dict:
        """Analyze the structure of a single conversation."""
        mapping = conversation.get('mapping', {})
        title = conversation.get('title', 'Untitled')
        conv_id = conversation.get('conversation_id', 'unknown')
        create_time = conversation.get('create_time')
        update_time = conversation.get('update_time')
        
        # Count messages by role and type
        role_counts = Counter()
        content_type_counts = Counter()
        message_count = 0
        models = set()
        
        for node_id, node in mapping.items():
            message_data = node.get('message')
            if not message_data:
                continue
                
            message_count += 1
            
            # Role analysis
            author = message_data.get('author', {})
            role = author.get('role', 'unknown')
            role_counts[role] += 1
            
            # Content type analysis
            content_data = message_data.get('content', {})
            content_type = content_data.get('content_type', 'text')
            content_type_counts[content_type] += 1
            
            # Model tracking
            metadata = message_data.get('metadata', {})
            model_slug = metadata.get('model_slug')
            if model_slug:
                models.add(model_slug)
        
        return {
            'title': title,
            'id': conv_id,
            'create_time': create_time,
            'update_time': update_time,
            'message_count': message_count,
            'role_counts': dict(role_counts),
            'content_type_counts': dict(content_type_counts),
            'models': list(models)
        }
    
    def extract_meaningful_content(self, conversation: Dict) -> List[str]:
        """Extract meaningful text content from conversation."""
        content_pieces = []
        mapping = conversation.get('mapping', {})
        
        skip_roles = {'system'}
        skip_content_types = {'user_editable_context', 'thoughts', 'reasoning_recap'}
        
        for node_id, node in mapping.items():
            message_data = node.get('message')
            if not message_data:
                continue
                
            # Check if we should skip this message
            author = message_data.get('author', {})
            role = author.get('role', 'unknown')
            content_data = message_data.get('content', {})
            content_type = content_data.get('content_type', 'text')
            
            if role in skip_roles or content_type in skip_content_types:
                continue
                
            # Extract text content
            parts = content_data.get('parts', [])
            if parts:
                content = '\n'.join(str(part) for part in parts if part)
                content = content.strip()
                if len(content) > 10:  # Skip very short content
                    content_pieces.append(content)
        
        return content_pieces
    
    def identify_topics(self, content_pieces: List[str]) -> List[str]:
        """Identify likely topics from content."""
        topics = []
        all_content = ' '.join(content_pieces).lower()
        
        # Technical topics
        tech_topics = {
            'python': ['python', 'py', 'pip', 'django', 'flask'],
            'javascript': ['javascript', 'js', 'node', 'npm', 'react', 'vue'],
            'web-development': ['html', 'css', 'website', 'frontend', 'backend'],
            'database': ['database', 'sql', 'postgres', 'mysql', 'supabase'],
            'ai-ml': ['ai', 'machine learning', 'gpt', 'openai', 'model', 'embedding'],
            'coding': ['code', 'programming', 'function', 'class', 'algorithm'],
            'data-science': ['data', 'analysis', 'pandas', 'numpy', 'visualization'],
            'devops': ['docker', 'kubernetes', 'aws', 'deployment', 'server'],
        }
        
        # Project/domain topics
        domain_topics = {
            'education': ['teach', 'learn', 'student', 'course', 'tutorial'],
            'business': ['project', 'client', 'meeting', 'deadline', 'budget'],
            'research': ['research', 'paper', 'study', 'analysis', 'findings'],
            'troubleshooting': ['error', 'bug', 'fix', 'problem', 'issue', 'debug'],
        }
        
        all_topics = {**tech_topics, **domain_topics}
        
        for topic, keywords in all_topics.items():
            if any(keyword in all_content for keyword in keywords):
                topics.append(topic)
        
        return topics
    
    def analyze_all_conversations(self) -> None:
        """Analyze all loaded conversations."""
        print(f"\n🔍 Analyzing {len(self.conversations)} conversations...")
        
        conversation_details = []
        
        for i, conversation in enumerate(self.conversations, 1):
            if i % 10 == 0:
                print(f"  📊 Processed {i}/{len(self.conversations)} conversations")
            
            # Analyze structure
            details = self.analyze_conversation_structure(conversation)
            conversation_details.append(details)
            
            # Update global stats
            self.stats['total_messages'] += details['message_count']
            self.stats['conversation_lengths'].append(details['message_count'])
            
            for role, count in details['role_counts'].items():
                self.stats['messages_by_role'][role] += count
            
            for content_type, count in details['content_type_counts'].items():
                self.stats['content_types'][content_type] += count
            
            for model in details['models']:
                self.stats['models_used'][model] += 1
            
            # Extract and analyze content
            content_pieces = self.extract_meaningful_content(conversation)
            topics = self.identify_topics(content_pieces)
            for topic in topics:
                self.stats['topics'][topic] += 1
            
            # Track date range
            create_time = details['create_time']
            if create_time:
                dt = datetime.fromtimestamp(create_time)
                if not self.stats['date_range']['earliest'] or dt < self.stats['date_range']['earliest']:
                    self.stats['date_range']['earliest'] = dt
                if not self.stats['date_range']['latest'] or dt > self.stats['date_range']['latest']:
                    self.stats['date_range']['latest'] = dt
        
        self.stats['total_conversations'] = len(self.conversations)
        
        # Store detailed conversation info for reporting
        self.conversation_details = conversation_details
    
    def print_analysis_report(self) -> None:
        """Print comprehensive analysis report."""
        print(f"\n{'='*80}")
        print(f"📊 SPARKY EXPORT ANALYSIS REPORT")
        print(f"{'='*80}")
        
        # Basic stats
        print(f"\n📈 OVERVIEW")
        print(f"  Total conversations: {self.stats['total_conversations']:,}")
        print(f"  Total messages: {self.stats['total_messages']:,}")
        
        if self.stats['conversation_lengths']:
            avg_length = sum(self.stats['conversation_lengths']) / len(self.stats['conversation_lengths'])
            print(f"  Average messages per conversation: {avg_length:.1f}")
            print(f"  Longest conversation: {max(self.stats['conversation_lengths'])} messages")
            print(f"  Shortest conversation: {min(self.stats['conversation_lengths'])} messages")
        
        # Date range
        if self.stats['date_range']['earliest'] and self.stats['date_range']['latest']:
            print(f"\n📅 DATE RANGE")
            print(f"  Earliest: {self.stats['date_range']['earliest'].strftime('%Y-%m-%d %H:%M')}")
            print(f"  Latest: {self.stats['date_range']['latest'].strftime('%Y-%m-%d %H:%M')}")
            duration = self.stats['date_range']['latest'] - self.stats['date_range']['earliest']
            print(f"  Duration: {duration.days} days")
        
        # Message roles
        print(f"\n👥 MESSAGE ROLES")
        for role, count in self.stats['messages_by_role'].most_common():
            percentage = (count / self.stats['total_messages']) * 100
            print(f"  {role}: {count:,} ({percentage:.1f}%)")
        
        # Content types
        print(f"\n📝 CONTENT TYPES")
        for content_type, count in self.stats['content_types'].most_common():
            percentage = (count / self.stats['total_messages']) * 100
            print(f"  {content_type}: {count:,} ({percentage:.1f}%)")
        
        # Models used
        if self.stats['models_used']:
            print(f"\n🤖 MODELS USED")
            for model, count in self.stats['models_used'].most_common():
                print(f"  {model}: {count} conversations")
        
        # Topics
        if self.stats['topics']:
            print(f"\n🏷️  IDENTIFIED TOPICS")
            for topic, count in self.stats['topics'].most_common(15):
                print(f"  {topic}: {count} conversations")
        
        # Top conversations by length
        print(f"\n📚 LONGEST CONVERSATIONS")
        sorted_convs = sorted(self.conversation_details, key=lambda x: x['message_count'], reverse=True)
        for conv in sorted_convs[:10]:
            print(f"  {conv['message_count']:3d} messages: {conv['title'][:60]}...")
        
        print(f"\n{'='*80}")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Analyze Sparky/ChatGPT export data structure and content'
    )
    parser.add_argument(
        'export_folder',
        help='Path to the chat-history export folder'
    )
    
    args = parser.parse_args()
    
    export_path = Path(args.export_folder)
    if not export_path.exists():
        print(f"❌ Export folder not found: {export_path}")
        sys.exit(1)
    
    conversations_file = export_path / 'conversations.json'
    if not conversations_file.exists():
        print(f"❌ conversations.json not found in {export_path}")
        sys.exit(1)
    
    try:
        analyzer = SparkyExportAnalyzer()
        
        if analyzer.load_conversations(conversations_file):
            analyzer.analyze_all_conversations()
            analyzer.print_analysis_report()
        
    except KeyboardInterrupt:
        print("\n⏹️  Analysis interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
