## 2026-05-20 - [Argument Injection Mitigation in Git Commands]
**Vulnerability:** User-controlled configuration values (like repository URLs or paths) passed directly to `git` subcommands (`ls-remote`, `clone`) via `subprocess.run` are vulnerable to argument injection if they start with a hyphen (e.g., `--upload-pack=malicious_command`).
**Learning:** Even when using lists in `subprocess.run` without `shell=True`, passing untrusted strings that begin with a hyphen to executables can be interpreted as flags, leading to arbitrary code execution or other unintended behavior.
**Prevention:** Always use the `--` separator in subprocess command lists before passing user-provided strings (paths or URLs) as positional arguments to ensure they are interpreted strictly as positional inputs (e.g., `['git', 'clone', '--', auth_url, str(path)]`).

## 2026-05-18 - [Credential Helper Log Leakage Prevention]
**Vulnerability:** The application executes `git` processes with an inline credential helper string (e.g. `credential.helper=!f() { echo username=token; echo password=$TOKEN; }; f`). The `sanitize_token` function only stripped passwords from URLs but left the credential helper string unmodified. If a `subprocess.CalledProcessError` occurs, this raw command is written out in logs/stacktraces.
**Learning:** Hardcoded commands with secrets in shell strings (like credential helpers) represent an often-overlooked path for secret leakage when dealing with process exceptions.
**Prevention:** Ensure `sanitize_token` explicitly scans for and redacts `echo password=...` assignments or any other similar inline secret injection patterns.

## 2024-05-18 - [Command Injection via Unsanitized Shell String Interpolation]
**Vulnerability:** A command injection vulnerability was present when generating default `verify_command`s (`test -d {package_path}`). User-controlled configuration paths were interpolated into shell strings without escaping, allowing arbitrary shell command execution if the path contained characters like `;` or quotes.
**Learning:** Shell strings generated dynamically from configuration values must always be sanitized. `shlex.quote()` is necessary, but it breaks shell-native features like tilde `~` expansion, meaning `os.path.expanduser` must be called *before* escaping the path.
**Prevention:** Use `shlex.quote(os.path.expanduser(path))` for all paths passed into shell command string interpolation.

## 2026-05-20 - [Argument Injection in NPM/NPX Commands]
**Vulnerability:** User-provided npm package names were being passed to `subprocess.run` (and internal wrappers like `run_process` / `run_version_command`) in `npm show`, `npm view`, and `npx` commands without separating positional arguments from flags. This could allow an attacker to inject arbitrary command-line arguments (e.g. `--eval`, `--script-shell`) by providing a malicious package name.
**Learning:** Even when passing arguments as a list to `subprocess.run` (shell=False), positional arguments that start with `-` or `--` will be interpreted as options/flags by the target executable (like npm/npx) unless explicitly separated.
**Prevention:** Always use the `--` separator before passing user-controlled variables as positional arguments to CLI tools (e.g., `npx --yes -- <package_name>` instead of `npx --yes <package_name>`).
