## 2026-05-18 - [Credential Helper Log Leakage Prevention]
**Vulnerability:** The application executes `git` processes with an inline credential helper string (e.g. `credential.helper=!f() { echo username=token; echo password=$TOKEN; }; f`). The `sanitize_token` function only stripped passwords from URLs but left the credential helper string unmodified. If a `subprocess.CalledProcessError` occurs, this raw command is written out in logs/stacktraces.
**Learning:** Hardcoded commands with secrets in shell strings (like credential helpers) represent an often-overlooked path for secret leakage when dealing with process exceptions.
**Prevention:** Ensure `sanitize_token` explicitly scans for and redacts `echo password=...` assignments or any other similar inline secret injection patterns.

## 2024-05-18 - [Command Injection via Unsanitized Shell String Interpolation]
**Vulnerability:** A command injection vulnerability was present when generating default `verify_command`s (`test -d {package_path}`). User-controlled configuration paths were interpolated into shell strings without escaping, allowing arbitrary shell command execution if the path contained characters like `;` or quotes.
**Learning:** Shell strings generated dynamically from configuration values must always be sanitized. `shlex.quote()` is necessary, but it breaks shell-native features like tilde `~` expansion, meaning `os.path.expanduser` must be called *before* escaping the path.
**Prevention:** Use `shlex.quote(os.path.expanduser(path))` for all paths passed into shell command string interpolation.
