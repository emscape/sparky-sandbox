# Sparky Chat History Ingestion Guide

## Overview

This guide helps you ingest your Sparky (ChatGPT) web export data into your AI memory system. The process intelligently parses conversation trees, extracts meaningful content, and stores it with appropriate metadata and embeddings.

## 🗂️ Export Structure Analysis

Your `chat-history` folder contains:

- **`conversations.json`** - Main conversation data with message trees
- **`chat.html`** - HTML viewer for conversations  
- **`user.json`** - Your user profile information
- **`message_feedback.json`** - Message ratings and feedback
- **`shared_conversations.json`** - Shared conversation metadata
- **Image files** - Screenshots and attachments from conversations
- **`dalle-generations/`** - AI-generated images
- **`user-{id}/`** - Additional user-specific files

## 🔍 Pre-Ingestion Analysis

Before ingesting, analyze your export to understand the content:

```bash
python analyze_sparky_export.py chat-history
```

This will show you:
- Total conversations and messages
- Date range of conversations  
- Message types and roles
- Identified topics and themes
- Models used (GPT-4, GPT-5, etc.)
- Longest/most active conversations

## 🚀 Ingestion Process

### Step 1: Review Analysis
Run the analysis script first to understand what you're ingesting:

```bash
python analyze_sparky_export.py chat-history
```

### Step 2: Test with Dry Run (Coming Soon)
```bash
python ingest_sparky_export.py chat-history --dry-run
```

### Step 3: Full Ingestion
```bash
python ingest_sparky_export.py chat-history
```

## 🎯 What Gets Ingested

### ✅ Included Content
- **User messages** - Your questions and inputs
- **Assistant responses** - Sparky's replies and explanations  
- **Meaningful system messages** - Important context
- **Code examples** - Programming discussions
- **Technical explanations** - Learning content
- **Problem-solving discussions** - Troubleshooting sessions

### ❌ Filtered Out
- **System metadata** - Internal ChatGPT system messages
- **User context prompts** - Profile/instruction messages
- **Reasoning thoughts** - Internal model reasoning
- **Very short messages** - Less than 10 characters
- **Empty content** - Null or whitespace-only messages

## 🏷️ Automatic Tagging

Messages are automatically tagged based on content:

### Technical Tags
- `python`, `javascript`, `web`, `database`, `ai`
- `coding`, `troubleshooting`, `tutorial`

### Context Tags  
- `sparky-export`, `chat-history`
- `role-user`, `role-assistant`
- `stellarus`, `education` (when relevant)

### Importance Levels (1-5)
- **5 (Critical)** - Not used for chat history
- **4 (High)** - Error discussions, urgent problems
- **3 (Medium)** - Technical content, learning discussions  
- **2 (Normal)** - General conversation, explanations
- **1 (Low)** - Very short messages, casual chat

## 📊 Processing Details

### Message Processing
1. **Parse conversation tree** - Extract messages from nested structure
2. **Filter content** - Remove system messages and metadata
3. **Generate embeddings** - Create vector representations
4. **Determine importance** - Analyze content for relevance
5. **Generate tags** - Identify topics and context
6. **Store with metadata** - Preserve conversation context

### Batch Processing
- Processes 3 messages at a time to avoid rate limits
- Exponential backoff retry logic for API failures
- Progress tracking with detailed logging
- Graceful handling of interruptions

### Metadata Preservation
Each message stores:
- Original conversation ID and title
- Message role (user/assistant)
- Creation timestamp
- Parent message relationship
- Model used (GPT-4, GPT-5, etc.)
- Request ID for debugging

## 🔧 Configuration Options

### Content Filtering
Edit `ingest_sparky_export.py` to customize:

```python
# Skip these message roles
self.skip_roles = {'system'}

# Skip these content types  
self.skip_content_types = {'user_editable_context', 'thoughts', 'reasoning_recap'}

# Minimum content length
self.min_content_length = 10
```

### Importance Scoring
Modify `determine_message_importance()` to adjust scoring:
- High importance keywords: error, problem, critical, urgent
- Medium importance: code, technical terms, learning content
- Default importance: 2 (normal conversation)

### Tag Generation
Customize `generate_message_tags()` to add project-specific tags:
- Add your company/project keywords
- Include domain-specific terminology
- Modify technical keyword lists

## 📈 Expected Results

For a typical export with ~100 conversations:
- **Processing time**: 10-30 minutes (depending on content volume)
- **Success rate**: 95%+ (with retry logic)
- **Storage**: ~1-5MB in database (text + embeddings)
- **Searchable content**: All meaningful messages with full context

## 🔍 Post-Ingestion Verification

After ingestion, verify the results:

```bash
# Test database connectivity
python test_connectivity.py

# Search for specific content
python retrieve_similar.py "python coding examples" --limit 5

# Check recent ingestions
python retrieve_similar.py "sparky-export" --tags sparky-export --limit 10
```

## 🛠️ Troubleshooting

### Common Issues

**Rate Limiting**
- Reduce batch size in `process_conversation()`
- Increase delays between batches
- Check OpenAI API usage limits

**Memory Errors**
- Process conversations in smaller chunks
- Increase system memory if possible
- Monitor memory usage during processing

**Database Connection Issues**
- Verify Supabase credentials in `.env`
- Check network connectivity
- Ensure database is not paused

**Content Parsing Errors**
- Check for malformed JSON in export
- Verify export completeness
- Review conversation structure

### Recovery Strategies
- **Partial failures**: Successfully processed messages remain in database
- **Interruption recovery**: Re-run script to continue from where it left off
- **Duplicate prevention**: Messages are deduplicated by content hash

## 🔄 Integration with Existing System

The ingested Sparky data integrates seamlessly:
- **Same database schema** - Uses existing `structured_memory` table
- **Compatible search** - Works with `retrieve_similar.py`
- **Consistent metadata** - Follows established tagging conventions
- **Embedding compatibility** - Uses same OpenAI embedding model

## 📝 Next Steps

After successful ingestion:

1. **Test retrieval** - Search for specific topics from your conversations
2. **Refine tags** - Add custom tags for better organization  
3. **Monitor usage** - Track how the ingested content helps with context
4. **Regular updates** - Re-export and ingest new conversations periodically

## 🎯 Best Practices

- **Start small** - Test with analysis before full ingestion
- **Monitor progress** - Watch for errors and adjust batch sizes
- **Verify results** - Test search functionality after ingestion
- **Backup first** - Ensure you have backups of both export and database
- **Document custom changes** - Note any modifications to filtering or tagging

This comprehensive ingestion system transforms your Sparky conversation history into a searchable, contextual knowledge base that enhances your AI memory system's capabilities!
