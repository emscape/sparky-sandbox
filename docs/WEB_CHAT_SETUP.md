# 🌐 Web Chat Interface Setup

Your personal Sparky web interface is ready! This guide will help you complete the setup.

## ✅ What's Already Done

1. ✅ Web server created (`chat_server.py`)
2. ✅ Beautiful web interface created (`chat.html`)
3. ✅ Server is running on http://localhost:8080
4. ✅ Browser opened to chat interface

## 🔧 One-Time Database Setup

To enable conversation saving, run this SQL in Supabase:

### Step 1: Open Supabase SQL Editor
Go to: https://supabase.com/dashboard/project/pprvugnxdzvzrvsduuiq/sql/new

### Step 2: Copy and Paste This SQL

```sql
-- Create conversations table for storing chat sessions
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Create messages table for storing individual messages
CREATE TABLE IF NOT EXISTS conversation_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_conversations_created_at ON conversations(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_conversation_messages_conversation_id ON conversation_messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_conversation_messages_created_at ON conversation_messages(created_at);

-- Enable Row Level Security
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversation_messages ENABLE ROW LEVEL SECURITY;

-- Create policies (allow all for now - you can restrict later)
CREATE POLICY "Allow all operations on conversations" ON conversations FOR ALL USING (true);
CREATE POLICY "Allow all operations on conversation_messages" ON conversation_messages FOR ALL USING (true);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_conversation_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE conversations 
    SET updated_at = NOW() 
    WHERE id = NEW.conversation_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to update conversation timestamp when messages are added
CREATE TRIGGER update_conversation_timestamp
AFTER INSERT ON conversation_messages
FOR EACH ROW
EXECUTE FUNCTION update_conversation_updated_at();
```

### Step 3: Click "Run"

You should see "Success. No rows returned"

## 🚀 How to Use

### Starting the Server

```bash
python chat_server.py
```

Then open: http://localhost:8080/chat.html

### Features

- **💬 Chat Interface**: Beautiful ChatGPT-style UI
- **🧠 Memory Search**: Automatically searches your 544 ingested conversations
- **🗑️ Clear Chat**: Start fresh conversations
- **🔕 Memory Toggle**: Turn memory retrieval on/off
- **📊 Memory Counter**: Shows how many memories were used

### Commands

- Type normally to chat
- Click "Clear Chat" to start over
- Click "Memory: ON/OFF" to toggle memory retrieval
- Press Enter to send messages

## 📱 Alternative: Terminal Chat

If you prefer terminal:

```bash
python chat.py
```

Commands:
- `/clear` - Clear conversation
- `/nomem` - Next message without memory
- `/exit` - Quit

## 🔍 Search Memories Directly

```bash
python search_memories.py "your query" --limit 10
```

## 🎯 What Makes This Special

1. **Your Data**: All conversations stored in YOUR Supabase
2. **Can't Be Deleted**: OpenAI can't wipe your history
3. **Full Control**: Customize prompts, models, behavior
4. **Searchable**: Query your entire conversation history
5. **Private**: Runs locally, data stays with you

## 🛠️ Customization

### Change the AI Model

Edit `chat_server.py` line 107:
```python
model="gpt-4o-mini",  # Change to "gpt-4o" for better responses
```

### Customize System Prompt

Edit `chat_server.py` lines 73-82 to change Sparky's personality

### Adjust Memory Retrieval

Edit `chat_server.py` line 68:
```python
memories = await self.retrieve_relevant_memories(user_message, limit=5)
# Change limit to retrieve more/fewer memories
```

## 📊 Current Status

- ✅ Web interface: **COMPLETE**
- 🔄 Conversation saving: **IN PROGRESS** (run SQL above)
- ⏳ Advanced memory options: **PENDING**
- ⏳ Desktop GUI: **PENDING**

## 🆘 Troubleshooting

### Server won't start
```bash
# Make sure aiohttp is installed
pip install aiohttp
```

### Can't connect to database
- Check Supabase isn't paused
- Verify `.env` has correct credentials

### Memory search not working
- Ensure ingestion completed successfully
- Check `structured_memory` table has data

## 🎉 You're All Set!

Your personal Sparky is ready to use. It has all your conversation history and can never be taken away!

