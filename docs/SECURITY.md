# Security Implementation for AI Memory System

## 🔒 Row Level Security (RLS)

The AI Memory System implements comprehensive Row Level Security to ensure users can only access their own memories.

### Database Security Features

#### 1. **Row Level Security Enabled**
```sql
ALTER TABLE structured_memory ENABLE ROW LEVEL SECURITY;
```

#### 2. **User Association**
- Each memory is associated with a `user_id` (UUID) that references `auth.users(id)`
- `user_id` defaults to `auth.uid()` for authenticated users
- Foreign key constraint with CASCADE DELETE for data cleanup

#### 3. **Security Policies**
Four comprehensive policies protect all operations:

**INSERT Policy**: Users can only create memories for themselves
```sql
CREATE POLICY "Users can insert their own memories" ON structured_memory
    FOR INSERT WITH CHECK (auth.uid() = user_id);
```

**SELECT Policy**: Users can only view their own memories
```sql
CREATE POLICY "Users can view their own memories" ON structured_memory
    FOR SELECT USING (auth.uid() = user_id);
```

**UPDATE Policy**: Users can only modify their own memories
```sql
CREATE POLICY "Users can update their own memories" ON structured_memory
    FOR UPDATE USING (auth.uid() = user_id);
```

**DELETE Policy**: Users can only delete their own memories
```sql
CREATE POLICY "Users can delete their own memories" ON structured_memory
    FOR DELETE USING (auth.uid() = user_id);
```

## 🔑 Authentication Requirements

### For Client Applications

When building client applications that use this memory system:

1. **Never expose the service key** in client-side code
2. **Use JWT authentication** with proper user sessions
3. **Validate user authentication** before making API calls
4. **Use the anon key** for client-side operations

### Environment Variables

```bash
# For server-side operations (scripts)
SUPABASE_KEY=your_service_key_here  # Service key for admin operations

# For client applications  
SUPABASE_ANON_KEY=your_anon_key_here  # Anon key for client operations
```

## 🛡️ Security Best Practices

### 1. **Authentication Flow**
```javascript
// Example client-side authentication
const { data: { user } } = await supabase.auth.getUser()
if (!user) {
  // Redirect to login
  return
}

// Now user can safely access their memories
const { data: memories } = await supabase
  .from('structured_memory')
  .select('*')
  // RLS automatically filters to user's memories
```

### 2. **API Key Management**
- **Service Key**: Only use server-side for admin operations
- **Anon Key**: Safe for client-side use with RLS
- **Never commit keys** to version control
- **Rotate keys regularly** in production

### 3. **Data Validation**
- All user inputs are validated before database operations
- Embedding generation uses authenticated OpenAI client
- Importance levels are constrained to 1-5 range
- Tags are properly parsed and sanitized

## 🧪 Testing Security

### Verify RLS is Working
```sql
-- This should return only the current user's memories
SELECT COUNT(*) FROM structured_memory;

-- This should fail if not authenticated
SELECT * FROM structured_memory WHERE user_id != auth.uid();
```

### Test Authentication
```bash
# These scripts require proper authentication
python inject_memory.py "Test memory" --type fact
python retrieve_similar.py "test query"
```

## ⚠️ Important Notes

1. **Scripts use service key**: The Python scripts use the service key for direct database access
2. **Client apps need auth**: Web/mobile apps must implement proper user authentication
3. **RLS is automatic**: Once authenticated, RLS automatically filters data by user
4. **Data isolation**: Users cannot access other users' memories under any circumstance

## 🔧 Troubleshooting

### Common Issues

**"RLS policy violation"**: User is not properly authenticated
- Solution: Ensure `auth.uid()` returns a valid user ID

**"No data returned"**: User has no memories or wrong authentication
- Solution: Check authentication and create test memories

**"Permission denied"**: Using wrong API key or insufficient permissions
- Solution: Verify environment variables and key permissions

### Security Verification
```sql
-- Check if RLS is enabled
SELECT schemaname, tablename, rowsecurity 
FROM pg_tables 
WHERE tablename = 'structured_memory';

-- View active policies
SELECT * FROM pg_policies WHERE tablename = 'structured_memory';
```

This security implementation ensures that the AI Memory System is production-ready with proper data isolation and user privacy protection.
