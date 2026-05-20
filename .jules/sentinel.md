## 2024-05-18 - [Command Injection via Unsanitized Shell String Interpolation]
**Vulnerability:** A command injection vulnerability was present when generating default `verify_command`s (`test -d {package_path}`). User-controlled configuration paths were interpolated into shell strings without escaping, allowing arbitrary shell command execution if the path contained characters like `;` or quotes.
**Learning:** Shell strings generated dynamically from configuration values must always be sanitized. `shlex.quote()` is necessary, but it breaks shell-native features like tilde `~` expansion, meaning `os.path.expanduser` must be called *before* escaping the path.
**Prevention:** Use `shlex.quote(os.path.expanduser(path))` for all paths passed into shell command string interpolation.
