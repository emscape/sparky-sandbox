# Session Cookie Fix for HTTPS Authentication

## Problem Summary

The Sparky application was experiencing session persistence issues on Railway with HTTPS and custom domain. After successful OAuth login, the session cookie (`AIOHTTP_SESSION`) was not being set or persisted in the browser, causing users to be unable to access authenticated routes.

## Root Cause

The `EncryptedCookieStorage` in aiohttp was not configured with proper cookie attributes for HTTPS environments:
- Missing `secure=True` for HTTPS
- Missing `samesite` attribute for cross-site requests
- No explicit cookie configuration for production vs development

## Solution Implemented

### 1. Enhanced Cookie Configuration

Updated `app/main.py` to configure session cookies with proper security attributes:

```python
# Determine if we're in production (Railway) or local development
is_production = bool(os.getenv("RAILWAY_ENVIRONMENT"))

# Allow override of cookie security settings via environment
cookie_secure = os.getenv("COOKIE_SECURE", str(is_production)).lower() in ("true", "1", "yes")
cookie_samesite = os.getenv("COOKIE_SAMESITE", "Lax" if is_production else "None")

# Configure cookie storage with appropriate security settings
cookie_storage = EncryptedCookieStorage(
    secret_key,
    cookie_name="AIOHTTP_SESSION",
    secure=cookie_secure,  # Secure cookies for HTTPS
    httponly=True,  # Prevent XSS attacks
    samesite=cookie_samesite if cookie_samesite != "None" else None,
    max_age=86400  # 24 hours
)
```

### 2. Environment-Based Configuration

- **Production (Railway)**: `secure=True`, `samesite="Lax"`
- **Local Development**: `secure=False`, `samesite=None`
- **Override Options**: `COOKIE_SECURE` and `COOKIE_SAMESITE` environment variables

### 3. Enhanced Session Persistence

Added explicit session change marking in OAuth callback:

```python
session["supabase_access_token"] = access_token
session["supabase_refresh_token"] = refresh_token
session["user_id"] = user["id"]

# Force session to be saved by marking it as changed
session.changed()
```

### 4. Debug Enhancements

- Added debug logging for cookie configuration
- Added middleware to log cookie information
- Added `/api/session-test` endpoint for testing session persistence
- Enhanced debug output in OAuth callback

## Testing the Fix

### Local Testing

1. **Run the test script**:
   ```bash
   python test_session_fix.py
   ```

2. **Manual testing**:
   ```bash
   # Start the server
   python app/main.py
   
   # Test session persistence
   curl -c cookies.txt http://localhost:8080/api/session-test
   curl -b cookies.txt http://localhost:8080/api/session-test
   ```

### Production Testing (Railway)

1. **Deploy the updated code**
2. **Check debug logs** for cookie configuration
3. **Test OAuth flow**:
   - Go to `/api/auth/google`
   - Complete OAuth
   - Check browser dev tools for `AIOHTTP_SESSION` cookie
   - Verify cookie has `Secure` and `SameSite=Lax` attributes
4. **Test session persistence**:
   - Visit `/api/session-test` multiple times
   - Counter should increment (session persisting)

## Environment Variables

Add these to Railway for fine-tuned control:

```bash
# Force secure cookies (optional, auto-detected)
COOKIE_SECURE=true

# Set SameSite attribute (optional, defaults to "Lax" in production)
COOKIE_SAMESITE=Lax

# Ensure JWT secret is consistent across deploys
JWT_SECRET=your-secret-key-here
```

## Verification Checklist

- [ ] Local session test passes (`python test_session_fix.py`)
- [ ] Railway deployment successful
- [ ] Debug logs show correct cookie configuration
- [ ] OAuth login completes successfully
- [ ] Browser shows `AIOHTTP_SESSION` cookie with correct attributes
- [ ] `/api/auth/status` returns authenticated after login
- [ ] Protected routes accessible after login
- [ ] Session persists across page refreshes

## Troubleshooting

### If sessions still don't persist:

1. **Check browser dev tools**:
   - Network tab: Look for `Set-Cookie` headers
   - Application tab: Check if `AIOHTTP_SESSION` cookie exists
   - Verify cookie attributes: `Secure`, `HttpOnly`, `SameSite`

2. **Check server logs**:
   - Look for `[DEBUG] Session cookie config` messages
   - Check `[DEBUG] Request cookies` and `[DEBUG] Response cookies`
   - Verify session data is being stored

3. **Verify environment**:
   - `RAILWAY_ENVIRONMENT` should be set in production
   - `JWT_SECRET` should be consistent
   - Domain should match Supabase OAuth configuration

### Common Issues:

- **Mixed content**: Ensure all requests use HTTPS in production
- **Domain mismatch**: Cookie domain must match request domain
- **SameSite conflicts**: Try `SameSite=None` if cross-site issues persist
- **Browser blocking**: Some browsers block third-party cookies

## Next Steps

1. Deploy and test the fix
2. Monitor session persistence in production
3. Remove debug middleware once confirmed working
4. Consider implementing session refresh mechanism for long-lived sessions
