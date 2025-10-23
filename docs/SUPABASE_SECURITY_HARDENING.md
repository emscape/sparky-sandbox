# Supabase Security Hardening Guide

This guide covers remediation steps for common Supabase/Postgres security warnings detected by the database linter. Follow these instructions to improve your deployment's security posture.

## 1. Function Search Path Mutable

**Warning:** Functions like `public.update_conversation_updated_at` and `public.match_memories` have a mutable `search_path`.

**Why it matters:** A mutable search path can allow malicious users to hijack function calls by creating objects in the search path.

**How to fix:**
- Edit your migration SQL to set a fixed search path for each function. Example:

```sql
CREATE OR REPLACE FUNCTION public.match_memories(...)
RETURNS ... AS $$
  -- function body
$$ LANGUAGE plpgsql
SET search_path = public;
```

- Repeat for all affected functions.
- Deploy updated migrations to Supabase.

## 2. Extension in Public Schema

**Warning:** Extension `vector` is installed in the `public` schema.

**Why it matters:** Extensions in `public` can be accessed or altered by users with public privileges.

**How to fix:**
- Move the extension to a dedicated schema (e.g., `extensions`). Example:

```sql
CREATE SCHEMA IF NOT EXISTS extensions;
ALTER EXTENSION vector SET SCHEMA extensions;
```

- Update permissions as needed.

## 3. Leaked Password Protection Disabled

**Warning:** Supabase Auth is not checking passwords against HaveIBeenPwned.org.

**Why it matters:** Users may choose compromised passwords, increasing risk of account takeover.

**How to fix:**
- Go to Supabase dashboard → Authentication → Settings.
- Enable "Leaked password protection".

## References
- [Supabase Database Linter](https://supabase.com/docs/guides/database/database-linter)
- [Password Strength & Leaked Password Protection](https://supabase.com/docs/guides/auth/password-security#password-strength-and-leaked-password-protection)

## Checklist
- [ ] All functions have fixed search_path
- [ ] All extensions moved out of public schema
- [ ] Leaked password protection enabled in Supabase Auth

---

**After resolving the login issue, add this hardening task to the to-do list and follow the steps above.**
