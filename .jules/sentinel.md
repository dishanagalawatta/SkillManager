## 2024-05-14 - Fix Command Injection in `run_version_command`
**Vulnerability:** Found `subprocess.run(command, shell=True, ...)` which executes arbitrary commands directly from user-configurable configurations.
**Learning:** Configured commands or dynamically generated shell commands with `shell=True` can expose the application to command injections if inputs are untrusted or easily spoofed.
**Prevention:** Avoid `shell=True` and use `shlex.split(command)` combined with `shell=False` to safely execute shell commands.
