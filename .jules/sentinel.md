## 2024-05-14 - Fix Command Injection in `run_version_command`
**Vulnerability:** Found `subprocess.run(command, shell=True, ...)` which executes arbitrary commands directly from user-configurable configurations.
**Learning:** Configured commands or dynamically generated shell commands with `shell=True` can expose the application to command injections if inputs are untrusted or easily spoofed.
**Prevention:** Avoid `shell=True` and use `shlex.split(command)` combined with `shell=False` to safely execute shell commands.
## 2024-05-15 - Fix Argument Injection in Git Commands and System Open Tools
**Vulnerability:** Found argument injection vulnerability in `git clone`, `git ls-remote`, `open`, and `xdg-open` commands. When the repository URL or paths are generated dynamically and start with a hyphen (`-`), the tools treat them as command-line options instead of positional arguments, which can lead to arbitrary code execution or unintended behavior.
**Learning:** For executables that parse command-line arguments, arguments provided by user should be placed after `--` to explicitly indicate that the subsequent arguments are positional, regardless of their leading character.
**Prevention:** Always use `--` separator before positional arguments when interacting with shell executables using `subprocess.run()`.
