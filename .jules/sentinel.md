## 2024-05-15 - Command Injection in run_version_command

**Vulnerability:** Use of `shell=True` in `subprocess.run` with unvetted user-provided command strings allowed for arbitrary command execution.

**Learning:** Passing a raw string to `subprocess.run` with `shell=True` invokes the shell (`/bin/sh` or `cmd.exe`), which interprets shell metacharacters like `;`, `&`, and `|`. This makes the application vulnerable to command injection if any part of the string is user-controlled.

**Prevention:** Always use `shell=False` and pass the command as a list of tokens. Use `shlex.split()` to tokenize the command string safely. On Windows, ensure backslashes are preserved by doubling them before splitting with `shlex.split(posix=True)`, or handle platform-specific quoting differences carefully. Always catch `ValueError` from `shlex.split` and use a PATH-resolving helper like `_resolve_process_command` to ensure executables are found correctly without a shell.
