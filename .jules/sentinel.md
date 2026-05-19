
## 2026-05-18 - [Credential Helper Log Leakage Prevention]
**Vulnerability:** The application executes `git` processes with an inline credential helper string (e.g. `credential.helper=!f() { echo username=token; echo password=$TOKEN; }; f`). The `sanitize_token` function only stripped passwords from URLs but left the credential helper string unmodified. If a `subprocess.CalledProcessError` occurs, this raw command is written out in logs/stacktraces.
**Learning:** Hardcoded commands with secrets in shell strings (like credential helpers) represent an often-overlooked path for secret leakage when dealing with process exceptions.
**Prevention:** Ensure `sanitize_token` explicitly scans for and redacts `echo password=...` assignments or any other similar inline secret injection patterns.
