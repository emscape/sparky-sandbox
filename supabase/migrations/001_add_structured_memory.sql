-- Enable pgvector if not already enabled
create extension if not exists vector;

-- Create the structured_memory table
create table if not exists structured_memory (
  id uuid default gen_random_uuid() primary key,
  user_id uuid references auth.users(id) on delete cascade,
  content text not null,
  type text,
  tags text[],
  source text,
  importance integer default 1,
  embedding vector(1536),
  created_at timestamp with time zone default timezone('utc'::text, now()) not null,
  updated_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Enable Row Level Security
alter table structured_memory enable row level security;

-- Create RLS policies
create policy "Users can only see their own memories" on structured_memory
  for select using (auth.uid() = user_id);

create policy "Users can insert their own memories" on structured_memory
  for insert with check (auth.uid() = user_id);

create policy "Users can update their own memories" on structured_memory
  for update using (auth.uid() = user_id);

create policy "Users can delete their own memories" on structured_memory
  for delete using (auth.uid() = user_id);

-- Create indexes for better performance
create index if not exists structured_memory_user_id_idx on structured_memory(user_id);
create index if not exists structured_memory_embedding_idx on structured_memory using ivfflat (embedding vector_cosine_ops);
create index if not exists structured_memory_tags_idx on structured_memory using gin(tags);
