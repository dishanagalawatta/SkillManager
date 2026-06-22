## 2025-02-28 - Regex Over-Redaction Vulnerability
**Vulnerability:** `.*` was used to redact a secret token from multiline/compound terminal logs (`re.sub(r"(echo password=).*", r"\1***", text)`).
**Learning:** `.*` strips out trailing lines or chained commands after a password on the same line, resulting in data loss.
**Prevention:** Separate patterns for quoted and unquoted values. Handle spaces and escaped characters using escape-aware patterns (e.g., `r"(password=)(['\"])((?:\\.|(?!\\2)[^\\])*)\2"` to handle quotes dynamically, and `r"(password=)(?!['\"])([^;\r\n\s]+)"` for unquoted values, stopping at spaces/semicolons).
