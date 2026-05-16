## 2024-05-15 - [Sanitize Authentication Tokens in Process Logs]
**Vulnerability:** Subprocess outputs and `subprocess.CalledProcessError` exceptions leaked plaintext authentication tokens injected into git clone URLs.
**Learning:** Functions that execute subprocesses with authenticated endpoints (like `get_authenticated_url`) must actively sanitize their output streams and exception objects to prevent secrets from reaching terminal logs or UI output windows.
**Prevention:** Always wrap logging/emission layers and exception instantiation in a sanitization helper that strips sensitive `userinfo` components from URLs (e.g., `re.sub(r'(https?://)[^@/\s]+@', r'\1***@', text)`).
