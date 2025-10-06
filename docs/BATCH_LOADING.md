# Batch Memory Loading Guide

The `load_memory_batch.py` script enables efficient bulk loading of memories from text files into the AI memory system.

## 🚀 Features

- **Multi-format Support**: Process `.txt`, `.md`, and `.json` files
- **Intelligent Chunking**: Split content into ~500 token chunks with sentence boundary respect
- **Auto-detection**: Automatically detect source type from filename patterns
- **Async Processing**: Optimized batch processing with retry logic
- **Progress Tracking**: Real-time progress updates and comprehensive summaries
- **Error Resilience**: Skip empty chunks, handle malformed text gracefully
- **Metadata Support**: Full metadata tagging (type, source, tags, importance)

## 📋 Requirements

Install the additional dependency:
```bash
pip install tiktoken>=0.5.0
```

## 🔧 Usage

### Basic Usage
```bash
# Process a markdown file with auto-detected source
python load_memory_batch.py sample_chat.md

# Process a text file with custom tags
python load_memory_batch.py document.txt --tags="project,notes"
```

### Advanced Usage
```bash
# Full metadata specification
python load_memory_batch.py chat.md \
  --source=chat \
  --tags="sparky,emstyle,team" \
  --importance=3

# Process JSON data
python load_memory_batch.py data.json \
  --source=api \
  --importance=2
```

## 📁 Supported File Types

### Text Files (`.txt`)
- Plain text content
- Automatic encoding detection (UTF-8, Latin-1)
- Preserves formatting and structure

### Markdown Files (`.md`)
- Full markdown syntax support
- Headers, lists, code blocks preserved
- Ideal for documentation and chat logs

### JSON Files (`.json`)
- Converts structured data to readable text
- Handles objects, arrays, and primitive types
- Pretty-printed with proper indentation

## 🏷️ Source Auto-Detection

The script automatically detects source types from filename patterns:

| Filename Contains | Detected Source |
|-------------------|-----------------|
| `chat`, `conversation`, `messages` | `chat` |
| `blog`, `post`, `article` | `blog` |
| `email`, `mail` | `email` |
| `doc`, `documentation`, `readme` | `documentation` |
| `log`, `logs` | `log` |
| `note`, `notes` | `notes` |
| *other* | `file` |

## 🔪 Text Chunking Strategy

### Intelligent Splitting
- **Target Size**: ~500 tokens per chunk
- **Boundary Respect**: Splits at sentence boundaries when possible
- **Overlap**: Small overlap between chunks for context preservation
- **Long Content**: Handles oversized sentences by word-level splitting

### Quality Filters
- **Minimum Length**: Chunks must be >10 characters
- **Empty Removal**: Automatically skips empty or whitespace-only chunks
- **Text Cleaning**: Removes excessive whitespace and normalizes formatting

## ⚡ Performance Optimizations

### Batch Processing
- **Batch Size**: Processes 5 chunks simultaneously
- **Rate Limiting**: 1-second delay between batches
- **Memory Efficient**: Streams large files without loading entirely into memory

### Retry Logic
- **Exponential Backoff**: 2^attempt seconds delay
- **Max Retries**: 3 attempts per chunk
- **Graceful Degradation**: Continues processing even if some chunks fail

## 📊 Progress Tracking

### Real-time Updates
```
📁 Processing file: sample_chat.md
📄 File size: 3247 characters
🔪 Split into 8 chunks
🚀 Processing 8 chunks...
  📝 Processing chunk 1/8 (456 chars, ~123 tokens)
  📝 Processing chunk 2/8 (512 chars, ~138 tokens)
  ...
✅ Completed processing sample_chat.md
```

### Final Summary
```
📊 BATCH PROCESSING SUMMARY
============================================================
Total chunks processed: 8
Successfully stored: 8
Failed to store: 0
Skipped (empty): 0
Success rate: 100.0%
⏱️  Total processing time: 12.34 seconds
============================================================
```

## 🛡️ Security & Data Integrity

### Row Level Security
- All memories are automatically associated with the authenticated user
- RLS policies ensure data isolation between users
- No risk of cross-user data contamination

### Data Validation
- Content validation before embedding generation
- Metadata validation (importance 1-5, valid tags)
- Graceful handling of malformed input

## 🔧 CLI Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `filepath` | Required | - | Path to file (.txt, .md, .json) |
| `--source` | Optional | Auto-detected | Memory source type |
| `--tags` | Optional | None | Comma-separated tags |
| `--importance` | Optional | 1 | Importance level (1-5) |

## 📝 Examples

### Chat Log Processing
```bash
python load_memory_batch.py team_meeting.md \
  --source=chat \
  --tags="team,meeting,sparky" \
  --importance=3
```

### Documentation Import
```bash
python load_memory_batch.py api_docs.md \
  --source=documentation \
  --tags="api,reference" \
  --importance=4
```

### Email Archive
```bash
python load_memory_batch.py important_emails.txt \
  --source=email \
  --tags="client,important" \
  --importance=5
```

## ⚠️ Error Handling

### Common Issues

**File Not Found**
```
❌ Error: File not found: nonexistent.txt
```

**Unsupported Format**
```
❌ Error: Unsupported file type: .pdf
Supported types: .txt, .md, .json
```

**API Failures**
```
⚠️  Attempt 1 failed, retrying: Rate limit exceeded
❌ Failed to store chunk after 3 attempts: API error
```

### Recovery Strategies
- **Partial Success**: Script continues even if some chunks fail
- **Progress Preservation**: Successfully stored chunks remain in database
- **Detailed Logging**: Clear error messages for troubleshooting

## 🧪 Testing

Test with the provided sample file:
```bash
python load_memory_batch.py sample_chat.md \
  --source=chat \
  --tags="sparky,emstyle,test" \
  --importance=2
```

This will process the sample chat log and demonstrate all features of the batch loading system.

## 🔄 Integration

The batch loader integrates seamlessly with the existing memory system:
- Uses same database schema (`structured_memory`)
- Compatible with `retrieve_similar.py` for searching loaded content
- Respects all security policies and user isolation
- Maintains consistent metadata structure

Perfect for importing large amounts of historical data, documentation, or conversation logs into your AI memory system!
